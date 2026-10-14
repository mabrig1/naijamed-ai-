# Research job queue — initial API contract

Authenticated endpoints:

- `POST /api/research/jobs` — creates a private queued molecular-descriptor job with up to 20 SMILES.
- `GET /api/research/jobs` — lists the requesting user's 50 newest job summaries.
- `GET /api/research/jobs/{job_id}` — returns a job summary only to its owner.

Jobs are stored in MongoDB `research_jobs` with a random UUID and owner ID. Raw inputs are intentionally excluded from GET responses.

**Not yet a running queue:** This change stores jobs with status `queued`. No worker claims, executes, retries or completes them. Do not imply processing has started. No Kaggle connection is configured.

## Before production

1. Add per-user quotas, rate limiting, storage retention and data deletion policy.
2. Add a trusted worker with lease-based claiming, retry bounds, execution budgets and signed service authentication.
3. Restrict worker writes to status and sanitized results; encrypt sensitive stored inputs where applicable.
4. Add job lifecycle tests, owner isolation tests and concurrency tests.
5. Confirm MongoDB connectivity, runtime dependencies, CI and deployment environment.

Research-only results do not establish clinical efficacy or safety.
