# NigerFlora private R2 research storage (PREVIEW STAGING ONLY)

This work **does not create** an R2 bucket or connect it to Cloudflare
production. The previous screenshot only established the proposed bucket
name \`nigerflora-storage\`, not that bucket creation completed.

Once you verify the bucket exists in Cloudflare R2 Object Storage, and only
after you approve staging, deploy using
\`cloudflare/wrangler.r2.preview.jsonc\`. This alternate config adds a private
binding \`NIGERFLORA_R2\` but does not attach public R2 domains.

The default \`cloudflare/wrangler.jsonc\` intentionally has **no R2 binding**,
so deploying from GitHub does not fail before the bucket exists. Both
\`STORAGE_ENABLED\` and \`R2_WRITES_ENABLED\` start false. For storage to be
usable, a verified owner must additionally authorize backend authentication
and API write gates; no secret values are stored in the repository.

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
