# NigerFlora — Python Function Size Reduction

Vercel reported a **256.86 MB** optimized serverless bundle against an enforced
**225 MB** limit (13 Nov 2026, deploy `dpl_4e691knqkYEh1SNiUuGpYAYmtZyk`).
This branch replaces the LangGraph package (only a fixed 5-node execution graph
was used) with a behavior-equivalent deterministic sequence, and replaces the
Gemini gRPC SDK with lightweight `httpx` calls to official Gemini REST routes.
The unused Anthropic requirement was also dropped from the root runtime.

The clinical workflow still runs red-flag guardrails FIRST, blocks non-medical
requests, bypasses LLM triage for emergencies, and never fabricates evidence
when the AI/embedding provider is not configured or unavailable. The vision
endpoint returns a clear 502 when the provider is unavailable instead of a
fabricated result. No payment, authentication or data model changes.

Use a **Preview** deployment of PR #27 with Vercel Root Directory set to the
repository root; inspect the function size and verify these routes:

- GET `/api/research-commerce` (public JSON catalog, 7 services)
- GET `/api/research-studio` (research JSON)
- GET `/api/discovery` (discovery JSON)
- POST order and payment callbacks, with TEST credentials and no charge
- No clinical response should silently downgrade a red-flag case

Regression checks:

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_lightweight_clinical_runtime.py' -v
npm ci --prefix frontend
npm run build --prefix frontend
```

**Do not merge to main or promote to production until the Vercel preview
build and end-to-end API checks pass.** The official Gemini SDK remains an
optional backend-only dependency for legacy deployments; Vercel root
requirements now use the REST transport.
