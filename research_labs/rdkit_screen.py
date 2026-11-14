"""Reproducible, offline RDKit drug-likeness screening for research compounds.

Usage:
    python research_labs/rdkit_screen.py -i compounds.csv -o descriptors.csv

This performs deterministic 2D cheminformatics calculations only.
It does NOT predict safety, efficacy, bioavailability, binding affinity,
clinical benefit, ADMET, or docking energies.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from rdkit import Chem, __version__ as rdkit_version
from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors

MAX_COMPOUNDS = 250
MAX_FILE_BYTES = 2 * 1024 * 1024
FIELDS = (
    "compound", "smiles", "canonical_smiles", "molecular_formula",
    "molecular_weight_g_mol", "clogp", "tpsa_a2", "hbond_donors",
    "hbond_acceptors", "rotatable_bonds", "qed", "lipinski_violations",
    "lipinski_rule_of_five", "status", "error", "rdkit_version",
)


def analyze_smiles(smiles: str, compound: str = "") -> dict[str, str | int | float]:
    """Calculate 2D descriptors; invalid entries return a per-row error."""
    result: dict[str, str | int | float] = {field: "" for field in FIELDS}
    result.update({"compound": str(compound)[:120], "smiles": str(smiles)[:512],
                   "status": "invalid", "rdkit_version": rdkit_version})
    if not isinstance(smiles, str) or not (1 <= len(smiles.strip()) <= 512):
        result["error"] = "SMILES must be 1 to 512 characters"
        return result
    try:
        mol = Chem.MolFromSmiles(smiles.strip(), sanitize=True)
        if mol is None:
            result["error"] = "Invalid SMILES"
            return result
        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        violations = sum((mw > 500, logp > 5, hbd > 5, hba > 10))
        result.update({
            "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
            "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
            "molecular_weight_g_mol": round(mw, 3),
            "clogp": round(logp, 3),
            "tpsa_a2": round(rdMolDescriptors.CalcTPSA(mol), 3),
            "hbond_donors": hbd,
            "hbond_acceptors": hba,
            "rotatable_bonds": Lipinski.NumRotatableBonds(mol),
            "qed": round(QED.qed(mol), 4),
            "lipinski_violations": violations,
            "lipinski_rule_of_five": "pass" if violations <= 1 else "fail",
            "status": "computed",
        })
    except (ValueError, RuntimeError, OverflowError) as exc:
        result["error"] = f"RDKit could not process molecule: {type(exc).__name__}"
    return result


def screen_csv(input_file: Path, output_file: Path) -> dict[str, int]:
    if not input_file.exists() or input_file.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Input CSV is missing or exceeds 2 MB")
    if input_file.resolve() == output_file.resolve():
        raise ValueError("Input and output paths must differ")
    with input_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "smiles" not in reader.fieldnames:
            raise ValueError("Input CSV must have a 'smiles' column")
        rows = []
        for i, row in enumerate(reader, start=1):
            if i > MAX_COMPOUNDS:
                raise ValueError(f"Maximum batch size is {MAX_COMPOUNDS} compounds")
            rows.append(analyze_smiles(row.get("smiles", ""), row.get("compound", "") or ""))
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {"total": len(rows), "computed": sum(x["status"] == "computed" for x in rows),
            "invalid": sum(x["status"] != "computed" for x in rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline RDKit compound descriptor screening")
    parser.add_argument("-i", "--input", required=True, type=Path, help="CSV with smiles,compound headers")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Results CSV")
    args = parser.parse_args()
    summary = screen_csv(args.input, args.output)
    print(f"Processed {summary['total']} molecules: {summary['computed']} computed, "
          f"{summary['invalid']} invalid. RDKit {rdkit_version}.")
    print("Note: drug-likeness heuristics do not imply efficacy, safety, ADMET, or clinical suitability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
