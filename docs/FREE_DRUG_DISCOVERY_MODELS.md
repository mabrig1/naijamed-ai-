# NigerFlora free computational pharmacology architecture

This repository supports two distinct components:

1. **AI research explanation** (Cloudflare Worker): a free-only OpenRouter
   language model assists interpretation of VALIDATED results and research
   methodology. It does not generate real molecular descriptors, docking
   scores, ADMET predictions, or binding affinities.
2. **Scientific calculation engines** (separate Python/CPU/GPU runtimes):
   RDKit for SMILES/descriptors; DeepChem for trained molecular property
   prediction; AutoDock Vina for docking; Boltz-2 for structure and
   binding affinity inference.

## Free-only research assistant (staged)

GET /api/drug-discovery/models returns capabilities and implementation
readiness. POST /api/drug-discovery/interpret is **disabled by default**.

Primary model ID: nvidia/nemotron-3-ultra-550b-a55b:free
Fallback model ID: openrouter/free

OpenRouter free models change availability and rate limits. The application
must NEVER automatically select a paid model. The OpenRouter API key is kept
as a Cloudflare Secret, never in front-end JavaScript or GitHub.

The Worker requires all three prerequisites before sending a prompt:
- RESEARCH_AI_ENABLED=true (initially false in Wrangler)
- OPENROUTER_API_KEY present in Cloudflare Secrets
- API_PROXY_ENABLED=true and an allowlisted BACKEND_ORIGIN able to validate
  a real signed-in user on GET /api/auth/me

A request must include the signed-in Bearer token, explicit
consent_to_external_ai=true, and a short non-sensitive prompt. Avoid sending
identifiable patient records, proprietary research datasets, unpublished
confidential data, passwords, or personally identifiable clinical content to
external model vendors. A real-world rollout needs per-user quotas, consent
records, retention controls and provider data-policy review.

The assistant is grounded only in user-supplied VERIFIED results. Its
outputs are not FDA/NAFDAC approvals, preclinical validation, assays, or
professional clinical advice.

## Offline RDKit calculations — runnable without Cloudflare

Run in a separate Python environment with sufficient resources:

    pip install rdkit
    python research_labs/rdkit_screen.py --input compounds.csv --output results.csv
    python -m unittest discover -s research_labs -p "test_rdkit_screen.py" -v

The input file has headers:

    compound,smiles
    aspirin,CC(=O)Oc1ccccc1C(=O)O
    ethanol,CCO

The result provides canonical SMILES, formula, molecular weight, predicted
cLogP (fragment method), topological polar surface area, H-bond donor and
acceptor counts, rotatable bonds, QED, and a Lipinski Rule of Five screen.
These are chemistry calculations / heuristics. The QED and Lipinski measures
are NOT laboratory ADMET data or evidence of pharmacological action.
No drug discovery outcome is inferred from them.

Limit: 250 molecules, 2 MB input file, 512 characters per SMILES.
The RDKit library is **not** added to the Vercel Python serverless package,
which is size-sensitive. This laboratory currently runs offline only, not as
a live Cloudflare or Vercel API.

## Next scientific integrations — not deployed

- AutoDock Vina in isolated CPU workloads with receptor preparation,
  known docking box, ligand preparation, controls and pose/RMSD analysis.
- DeepChem with documented training datasets, external validation, applicability
  domain and reproducible splits; an untrained model cannot claim ADMET accuracy.
- Boltz-2 protein–ligand affinity and structure inference on appropriately
  provisioned GPU nodes; model weights can be free while GPU compute is not.
- Clear audit provenance: input files + versions + settings + date + scripts.
- Private R2 for encrypted research outputs only after the bucket exists,
  user auth and authorization tests, access policy, malware scanning and
  privacy review.

No purchase, publishing, R2 binding, deployment of computational engines,
change of production domain, or activation of paid inference is included.

Official references:
- https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free
- https://openrouter.ai/openrouter/free
- https://www.rdkit.org/docs/Overview.html
- https://autodock-vina.readthedocs.io/en/stable/
- https://deepchem.readthedocs.io/en/stable/
- https://github.com/jwohlwend/boltz
