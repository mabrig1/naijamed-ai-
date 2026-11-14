/**
 * Private R2 research-file preview. Explicitly disabled until the R2 bucket,
 * backend identity contract, consent, scanning and quotas are verified.
 * No direct public object URL and no support for patient/clinical uploads.
 */
const PREFIX = "/api/research-files";
const MAX_BYTES = 10 * 1024 * 1024;
const MAX_FILES = 30;
const ID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i;
const JSON_HEADERS = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
const TYPES = new Set(["application/pdf", "application/json", "text/csv", "text/plain",
  "text/tab-separated-values", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "image/png", "image/jpeg"]);

const json = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });
const yes = value => value === "true";

async function getResearcher(request, origin) {
  if (!origin) return null;
  const auth = request.headers.get("Authorization") || "";
  if (!/^Bearer [A-Za-z0-9._~-]{10,4096}$/.test(auth)) return null;
  try {
    const res = await fetch(new URL("/api/auth/me", origin), {
      headers: { Accept: "application/json", Authorization: auth },
      redirect: "manual", signal: AbortSignal.timeout(8000),
    });
    if (res.status !== 200 || !(res.headers.get("Content-Type") || "").includes("application/json")) return null;
    const identity = await res.json();
    const id = String(identity?.id ?? "");
    // Reject unauthorised account classes, inactive users and malformed IDs.
    if (identity?.is_active === false || !["researcher", "admin"].includes(identity?.role) ||
        !/^[A-Za-z0-9_-]{1,80}$/.test(id)) return null;
    return id;
  } catch {
    return null;
  }
}

async function readFileBody(request) {
  const stream = request.body;
  if (!stream) return null;
  const reader = stream.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  if (total === 0) return null;
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
  return bytes;
}

export async function handleResearchFiles(request, env, origin) {
  const url = new URL(request.url);
  const path = url.pathname;
  const fileId = path === PREFIX ? "" : path.startsWith(PREFIX + "/") ? path.slice(PREFIX.length + 1) : null;
  if (fileId === null || (fileId && !ID.test(fileId))) {
    return json({ detail: "Invalid file ID" }, 400);
  }
  if (!yes(env.STORAGE_ENABLED) || !env.NIGERFLORA_R2) {
    return json({ detail: "Private research storage is not enabled" }, 503);
  }
  const id = await getResearcher(request, origin);
  if (!id) return json({ detail: "Verified researcher or administrator login required" }, 401);
  const bucket = env.NIGERFLORA_R2;
  const prefix = "researchers/" + id + "/";
  const key = prefix + fileId;
  if (request.method === "GET" && fileId === "") {
    try {
      const found = await bucket.list({ prefix, limit: MAX_FILES + 1 });
      return json({
        files: found.objects.slice(0, MAX_FILES).map(o => ({
          id: o.key.slice(prefix.length), size: o.size,
          name: o.customMetadata?.filename || "research-file",
        })),
        truncated: Boolean(found.truncated || found.objects.length > MAX_FILES),
      });
    } catch { return json({ detail: "Storage provider unavailable" }, 503); }
  }
  if (request.method === "GET" && fileId) {
    try {
      const file = await bucket.get(key);
      if (!file) return json({ detail: "File not found" }, 404);
      const name = String(file.customMetadata?.filename || "research-file").replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 96);
      return new Response(file.body, { status: 200, headers: {
        "Content-Type": file.httpMetadata?.contentType || "application/octet-stream",
        "Content-Disposition": 'attachment; filename="' + name + '"',
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
      } });
    } catch { return json({ detail: "Storage provider unavailable" }, 503); }
  }
  if (!yes(env.R2_WRITES_ENABLED) || !yes(env.API_WRITES_ENABLED)) {
    return json({ detail: "Research file uploads and deletion are disabled in preview" }, 503);
  }
  if (request.method === "POST" && fileId === "") {
    const type = (request.headers.get("Content-Type") || "").split(";", 1)[0].trim().toLowerCase();
    if (!TYPES.has(type)) return json({ detail: "Unsupported file type" }, 415);
    const length = Number(request.headers.get("Content-Length"));
    if (Number.isFinite(length) && length > MAX_BYTES) return json({ detail: "Maximum file size is 10 MB" }, 413);
    const file = await readFileBody(request);
    if (!file) return json({ detail: "Empty or oversized file" }, 413);
    const original = request.headers.get("X-File-Name") || "research-file";
    const name = original.replace(/[^A-Za-z0-9._-]/g, "_").slice(0, 96) || "research-file";
    try {
      const found = await bucket.list({ prefix, limit: MAX_FILES });
      if (found.truncated || found.objects.length >= MAX_FILES) {
        return json({ detail: "Private file quota reached" }, 409);
      }
      const objectId = crypto.randomUUID();
      await bucket.put(prefix + objectId, file, {
        httpMetadata: { contentType: type, contentDisposition: "attachment" },
        customMetadata: { filename: name },
      });
      return json({ id: objectId, name, size: file.byteLength }, 201);
    } catch { return json({ detail: "Storage provider unavailable" }, 503); }
  }
  if (request.method === "DELETE" && fileId) {
    try {
      if (!(await bucket.head(key))) return json({ detail: "File not found" }, 404);
      await bucket.delete(key);
      return json({ deleted: true });
    } catch { return json({ detail: "Storage provider unavailable" }, 503); }
  }
  return json({ detail: "Method not allowed" }, 405);
}
