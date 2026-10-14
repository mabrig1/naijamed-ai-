# RDKit molecular structure analysis (experimental)

The module `backend/app/research/structures.py` provides deterministic parsing, canonical isomeric SMILES and basic molecular descriptors. It does **not** perform docking, toxicity prediction, ADMET modeling or clinical validation.

## Setup

Install an RDKit version compatible with the deployed Python runtime, for example `pip install rdkit` in an isolated research worker. RDKit is optional and is imported only when analysis is requested; this PR does not modify production dependency locks.

## Usage

```python
from backend.app.research.structures import analyze_smiles
print(analyze_smiles("CCO"))
```

## Integration gates

- Add a separately authenticated, rate-limited research endpoint or background worker before exposing calculations to users.
- Apply request size limits and CPU/time budgets.
- Test with representative salts, tautomers, stereoisomers, malformed inputs and larger molecules.
- Version and document the exact RDKit release and standardization protocol.
- Avoid using computed descriptors as evidence of safety, efficacy or therapeutic suitability.

This PR is backend preparation only; no UI or deployed API endpoint is provided.
