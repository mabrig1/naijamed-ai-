"""Research-only molecular structure validation. Requires RDKit in the runtime."""
from __future__ import annotations

from typing import Any


def analyze_smiles(smiles: str) -> dict[str, Any]:
    if not isinstance(smiles, str) or not smiles.strip() or len(smiles) > 2048:
        raise ValueError("SMILES must be a nonempty string of at most 2048 characters")
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
    except ImportError as exc:
        raise RuntimeError("RDKit is not installed; molecular validation is unavailable") from exc

    molecule = Chem.MolFromSmiles(smiles.strip(), sanitize=True)
    if molecule is None:
        return {"valid": False, "error": "SMILES parsing or sanitization failed"}
    return {
        "valid": True,
        "canonical_smiles": Chem.MolToSmiles(molecule, canonical=True, isomericSmiles=True),
        "molecular_formula": rdMolDescriptors.CalcMolFormula(molecule),
        "molecular_weight": round(Descriptors.MolWt(molecule), 3),
        "logp": round(Descriptors.MolLogP(molecule), 3),
        "h_bond_donors": int(Descriptors.NumHDonors(molecule)),
        "h_bond_acceptors": int(Descriptors.NumHAcceptors(molecule)),
        "tpsa": round(Descriptors.TPSA(molecule), 3),
        "rotatable_bonds": int(Descriptors.NumRotatableBonds(molecule)),
        "heavy_atoms": int(molecule.GetNumHeavyAtoms()),
        "notice": "Research-only calculated descriptors; not ADMET predictions or evidence of safety or efficacy.",
    }
