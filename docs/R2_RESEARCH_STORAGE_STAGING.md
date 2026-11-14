# NigerFlora private R2 research storage (PREVIEW STAGING ONLY)

The Cloudflare R2 dashboard screenshot confirms the owner created
`nigerflora-storage` using Standard storage, with Public Access disabled
and 0 B stored as of 14 November 2026.

The default preview Worker Wrangler configuration now contains an R2 binding
`NIGERFLORA_R2` targeting the existing `nigerflora-storage` bucket.
Bindings are private runtime references, not publicly available object URLs.

Crucially, `STORAGE_ENABLED=false`, `R2_WRITES_ENABLED=false`, and
`API_WRITES_ENABLED=false` are still the default values, so neither reading
nor uploading research objects is enabled merely by connecting the bucket.
The alternate `wrangler.r2.preview.jsonc` remains for explicit staging
but is not needed for the standard branch deployment.

Research file routes, currently fail-closed:
- GET /api/research-files : list current researcher's objects
- GET /api/research-files/{uuid} : download as attachment
- POST /api/research-files : raw file body, X-File-Name header
- DELETE /api/research-files/{uuid} : delete current researcher's file

Private objects are keyed by \`researchers/<verified backend user ID>/<uuid>\`,
never by user-controlled paths, with 10 MB/file and 30 files/user
preview limits. Only backend-verified researcher and admin roles can list,
download or modify. File writes additionally require two distinct feature
flags. These are **preview-only** limits, not atomic billing or compliance
quotas. The backend must correctly issue and validate researcher JWTs via
\`/api/auth/me\`. This contract must be tested on an authenticated backend
before enabling R2 storage.

Never upload patient-identifiable data, unpublished confidential clinical
trial datasets, biological samples' personal metadata or other regulated data
to this preview. Production requires malware scanning, data classification,
server-side authorization audits, retention/delete policy, encryption policy,
rate limiting, account-based storage quotas, and legal review.

Use Cloudflare's existing R2 Standard storage class for frequently accessed
files. An account's free allowance does not guarantee zero costs beyond
limits. Do not expose public R2 buckets or leak R2 access keys.
