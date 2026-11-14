/**
 * Research AI assistant: explanation only, never molecular computation.
 *
 * Computational engines (RDKit, DeepChem, AutoDock Vina and Boltz-2) need
 * independent Python/CPU/GPU runtimes; their numeric output must be recorded
 * separately and must never be fabricated by a text model.
 */
export const FREE_RESEARCH_MODELS = Object.freeze([
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "openrouter/free",
]);

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
};
const TYPES = new Set([
  "molecular_descriptor_interpretation",
  "docking_result_interpretation",
  "admet_methodology",
  "pharmaceutical_statistical_analysis",
  "drug_discovery_research_design",
]);
const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: JSON_HEADERS });

export function getDrugDiscoveryCatalog(env = {}, backendReady = false) {
  return {
    assistant: {
      preferred: FREE_RESEARCH_MODELS[0],
      fallback: FREE_RESEARCH_MODELS[1],
      provider: "OpenRouter",
      enabled: env.RESEARCH_AI_ENABLED === "true" && !!env.OPENROUTER_API_KEY && backendReady,
      capability: "Scientific research reasoning and interpretation, not validated numerical computation",
      free_model_pricing: "Free model IDs only; subject to provider rate limits and availability",
    },
    computational_engines: [
      {
        name: "RDKit", stage: "local Python research lab", gpu_required: false,
        capabilities: ["SMILES validation", "descriptors", "Lipinski screening", "molecular fingerprints"],
        live_worker_execution: false,
      },
      {
        name: "DeepChem", stage: "separate validated Python service", gpu_required: false,
        capabilities: ["train or evaluate molecular property prediction models", "ADMET dataset analysis"],
        live_worker_execution: false,
      },
      {
        name: "AutoDock Vina", stage: "separate CPU docking workstation", gpu_required: false,
        capabilities: ["protein–ligand docking", "binding pose search", "docking scores"],
        live_worker_execution: false,
      },
      {
        name: "Boltz-2", stage: "separate GPU inference service", gpu_required: true,
        capabilities: ["biomolecular complex structures", "binding affinity prediction"],
        live_worker_execution: false,
      },
    ],
    guardrails: [
      "No patient-identifiable or proprietary trial data should be submitted to third-party free AI providers",
      "LLM answers are not clinical evidence, drug safety validation or docking scores",
      "Scientific tools require separately provisioned, validated compute runtimes",
    ],
  };
}

async function verifyResearcher(request, origin) {
  if (!origin) return false;
  const authorization = request.headers.get("Authorization") || "";
  if (!/^Bearer [A-Za-z0-9._~-]{10,4096}$/.test(authorization)) return false;
  try {
    const response = await fetch(new URL("/api/auth/me", origin), {
      headers: { Authorization: authorization, Accept: "application/json" },
      redirect: "manual",
      signal: AbortSignal.timeout(8000),
    });
    if (response.status !== 200 ||
        !(response.headers.get("content-type") || "").toLowerCase().includes("application/json")) return false;
    const identity = await response.json();
    return Boolean(identity && identity.id && identity.is_active !== false);
  } catch {
    return false;
  }
}

export async function handleDrugDiscovery(request, env, origin) {
  const url = new URL(request.url);
  if (url.pathname === "/api/drug-discovery/models") {
    if (request.method !== "GET" && request.method !== "HEAD") {
      return json({ detail: "Method not allowed" }, 405);
    }
    const response = json(getDrugDiscoveryCatalog(env, Boolean(origin)));
    return request.method === "HEAD"
      ? new Response(null, { status: 200, headers: JSON_HEADERS })
      : response;
  }
  if (url.pathname !== "/api/drug-discovery/interpret") {
    return json({ detail: "Unknown drug-discovery route" }, 404);
  }
  if (request.method !== "POST") {
    return json({ detail: "Method not allowed" }, 405);
  }
  if (env.RESEARCH_AI_ENABLED !== "true" || !env.OPENROUTER_API_KEY) {
    return json({ detail: "Research AI is disabled until explicitly enabled" }, 503);
  }
  if (!(await verifyResearcher(request, origin))) {
    return json({ detail: "A verified researcher session is required" }, 401);
  }
  if (!(request.headers.get("content-type") || "").toLowerCase().startsWith("application/json")) {
    return json({ detail: "JSON content type required" }, 415);
  }

  let body;
  try {
    const contentLength = Number(request.headers.get("content-length"));
    if (Number.isFinite(contentLength) && contentLength > 5000) {
      return json({ detail: "Request is too large" }, 413);
    }
    const raw = await request.text();
    if (raw.length > 5000) return json({ detail: "Request is too large" }, 413);
    body = JSON.parse(raw);
  } catch {
    return json({ detail: "Invalid JSON" }, 400);
  }
  if (!body || !TYPES.has(body.task) ||
      body.consent_to_external_ai !== true ||
      typeof body.prompt !== "string" ||
      body.prompt.trim().length < 10 || body.prompt.length > 2000) {
    return json({
      detail: "Choose a supported task, write a 10–2000 character non-sensitive prompt, and consent to external AI processing",
    }, 400);
  }
  const messages = [
    {
      role: "system",
      content: "You are a cautious scientific research-assistance model specializing in computational pharmacology, cheminformatics and drug discovery. Explain methods or interpret explicitly provided validated outputs. Never invent RDKit descriptors, docking energies, ADMET predictions, affinity estimates, simulation outputs, references, citations, assays, clinical efficacy or safety. Clearly identify estimates and uncertainty. Do not claim to have executed RDKit, AutoDock Vina, DeepChem or Boltz-2. Suggest reproducible computational validation steps and cite sources only if actually supplied. Never diagnose or recommend clinical use. Exclude patient-identifiable/private trial data.",
    },
    {
      role: "user",
      content: "Task: " + body.task + "\n" + body.prompt.trim(),
    },
  ];
  for (const model of FREE_RESEARCH_MODELS) {
    try {
      const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + env.OPENROUTER_API_KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model,
          messages,
          temperature: 0.1,
          max_tokens: 900,
        }),
        redirect: "manual",
        signal: AbortSignal.timeout(20000),
      });
      // Never fall through to a paid model or expose the API key.
      if (response.status === 401 || response.status === 403) {
        return json({ detail: "AI credentials are not authorized" }, 503);
      }
      if (!response.ok ||
          !(response.headers.get("content-type") || "").toLowerCase().includes("application/json")) {
        continue;
      }
      const data = await response.json();
      const answer = data?.choices?.[0]?.message?.content;
      if (typeof answer !== "string" || !answer.trim()) continue;
      return json({
        answer: answer.slice(0, 12000),
        model_requested: model,
        model_served: typeof data.model === "string" ? data.model : model,
        free_model_only: true,
        computer_analysis_performed: false,
        disclaimer: "Research interpretation only; validate with independent scientific software and experimental evidence.",
      });
    } catch {
      // A free endpoint may be overloaded or time out; try the free router.
    }
  }
  return json({
    detail: "No free reasoning-model endpoint is currently available. No paid fallback was attempted.",
  }, 503);
}
