# Molecular descriptor API (research-only)

POST `/api/research/molecules/analyze` with a valid user Bearer access token.

Example body:

```json
{"smiles":["CCO","O=C=O"]}
```

The response returns individual molecular validity results, canonical isomeric SMILES, molecular formula, weight, logP, hydrogen-bond donor/acceptor counts, TPSA, rotatable bonds and heavy atom count.

- Requires optional RDKit in the API runtime.
- Limits requests to 20 SMILES, each at most 2048 characters.
- Only authenticated users with permitted roles can invoke the endpoint.
- This endpoint is synchronous and should be moved behind a rate-limited worker and execution time budget before production exposure.
- The API does not persist submitted SMILES.
- This does not predict ADMET, toxicity, binding affinity, efficacy or clinical safety.

This branch builds on the RDKit module in PR #19. It is not production-ready without dependency pinning, tests, rate limiting and deployment verification.
