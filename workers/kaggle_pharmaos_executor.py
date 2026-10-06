from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import requests
from rdkit import Chem
from rdkit.Chem import AllChem

HTTP_HEADERS = {"User-Agent": "MABRIG-PharmaOS-Kaggle-Worker/1.0"}
JOB_ROOT = Path("/kaggle/working/pharmaos_jobs")


def _run(command: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout[-4000:]}\nSTDERR:\n{completed.stderr[-4000:]}"
        )
    return completed.stdout + "\n" + completed.stderr


def _download(url: str, path: Path) -> None:
    response = requests.get(url, headers=HTTP_HEADERS, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)


def _prepare_receptor(pdb_id: str, workdir: Path) -> tuple[Path, dict[str, Any]]:
    raw_pdb = workdir / f"{pdb_id}.pdb"
    clean_pdb = workdir / f"{pdb_id}_protein_only.pdb"
    _download(f"https://files.rcsb.org/download/{pdb_id}.pdb", raw_pdb)

    kept = []
    stripped_hetero = 0
    stripped_water = 0
    for line in raw_pdb.read_text(errors="ignore").splitlines():
        if line.startswith("ATOM"):
            kept.append(line)
        elif line.startswith("HETATM"):
            resname = line[17:20].strip().upper()
            if resname in {"HOH", "WAT", "DOD"}:
                stripped_water += 1
            else:
                stripped_hetero += 1
        elif line.startswith("TER"):
            kept.append(line)
    kept.append("END")
    clean_pdb.write_text("\n".join(kept) + "\n")

    base = workdir / "receptor"
    _run(
        [
            "mk_prepare_receptor.py",
            "--read_pdb",
            str(clean_pdb),
            "-o",
            str(base),
            "-p",
            "--delete_bad_res",
        ],
        cwd=workdir,
    )

    candidates = [
        workdir / "receptor.pdbqt",
        workdir / "receptor_rigid.pdbqt",
        *sorted(workdir.glob("receptor*.pdbqt")),
    ]
    receptor_pdbqt = next((p for p in candidates if p.exists() and p.stat().st_size > 0), None)
    if receptor_pdbqt is None:
        raise RuntimeError("Meeko did not create a receptor PDBQT file")

    return receptor_pdbqt, {
        "pdb_id": pdb_id,
        "source": "RCSB PDB",
        "preparation": "Meeko protein-only rigid receptor",
        "waters_removed": stripped_water,
        "heteroatom_records_removed": stripped_hetero,
        "note": "Review cofactors/metals before publication-grade interpretation; this default worker strips HETATM records.",
    }


def _pubchem_3d_sdf(cid: str, path: Path) -> None:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/record/SDF?record_type=3d"
    response = requests.get(url, headers=HTTP_HEADERS, timeout=60)
    if response.ok and len(response.content) > 100:
        path.write_bytes(response.content)
        return

    smiles_url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/"
        "CanonicalSMILES/JSON"
    )
    smiles_response = requests.get(smiles_url, headers=HTTP_HEADERS, timeout=60)
    smiles_response.raise_for_status()
    rows = smiles_response.json().get("PropertyTable", {}).get("Properties", [])
    if not rows:
        raise RuntimeError(f"PubChem did not return a structure for CID {cid}")
    smiles = rows[0].get("ConnectivitySMILES") or rows[0].get("CanonicalSMILES")
    if not smiles:
        raise RuntimeError(f"PubChem did not return SMILES for CID {cid}")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise RuntimeError(f"RDKit could not parse PubChem SMILES for CID {cid}")
    mol = Chem.AddHs(mol)
    status = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if status != 0:
        raise RuntimeError(f"RDKit could not generate a 3D conformer for CID {cid}")
    try:
        AllChem.UFFOptimizeMolecule(mol, maxIters=500)
    except Exception:
        pass
    writer = Chem.SDWriter(str(path))
    writer.write(mol)
    writer.close()


def _prepare_ligand(cid: str, workdir: Path) -> Path:
    sdf = workdir / f"cid_{cid}.sdf"
    pdbqt = workdir / f"cid_{cid}.pdbqt"
    _pubchem_3d_sdf(cid, sdf)
    _run(["mk_prepare_ligand.py", "-i", str(sdf), "-o", str(pdbqt)], cwd=workdir)
    if not pdbqt.exists() or pdbqt.stat().st_size == 0:
        raise RuntimeError(f"Meeko did not create ligand PDBQT for CID {cid}")
    return pdbqt


def _parse_vina_results(path: Path) -> list[dict[str, float]]:
    modes: list[dict[str, float]] = []
    pattern = re.compile(
        r"REMARK VINA RESULT:\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)"
    )
    for line in path.read_text(errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            modes.append(
                {
                    "affinity_kcal_mol": float(match.group(1)),
                    "rmsd_lb": float(match.group(2)),
                    "rmsd_ub": float(match.group(3)),
                }
            )
    return modes


def pharmaos_execute_job(job: dict[str, Any]) -> dict[str, Any]:
    manifest = job.get("manifest") or {}
    receptor = manifest.get("receptor") or {}
    ligands = manifest.get("ligands") or []
    params = manifest.get("parameters") or {}

    pdb_id = str(receptor.get("pdb_id") or "").strip().upper()
    if len(pdb_id) != 4:
        raise ValueError("Manifest receptor.pdb_id must be a valid 4-character PDB ID")
    if not ligands:
        raise ValueError("Manifest must contain at least one PubChem ligand")

    for key in ("center_x", "center_y", "center_z", "size_x", "size_y", "size_z"):
        if key not in params:
            raise ValueError(f"Manifest parameter {key} is required")

    job_id = str(job.get("id") or "manual-job")
    workdir = JOB_ROOT / job_id
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    receptor_pdbqt, receptor_meta = _prepare_receptor(pdb_id, workdir)
    ligand_results = []

    for ligand in ligands:
        cid = str(ligand.get("pubchem_cid") or "").strip()
        if not cid.isdigit():
            raise ValueError(f"Invalid PubChem CID: {cid!r}")

        ligand_pdbqt = _prepare_ligand(cid, workdir)
        out_pdbqt = workdir / f"cid_{cid}_docked.pdbqt"

        command = [
            "vina",
            "--receptor",
            str(receptor_pdbqt),
            "--ligand",
            str(ligand_pdbqt),
            "--center_x",
            str(float(params["center_x"])),
            "--center_y",
            str(float(params["center_y"])),
            "--center_z",
            str(float(params["center_z"])),
            "--size_x",
            str(float(params["size_x"])),
            "--size_y",
            str(float(params["size_y"])),
            "--size_z",
            str(float(params["size_z"])),
            "--exhaustiveness",
            str(int(float(params.get("exhaustiveness", 8)))),
            "--num_modes",
            str(int(float(params.get("num_modes", 9)))),
            "--seed",
            str(int(float(params.get("seed", 0)))),
            "--out",
            str(out_pdbqt),
        ]
        stdout = _run(command, cwd=workdir)
        modes = _parse_vina_results(out_pdbqt)
        ligand_results.append(
            {
                "pubchem_cid": cid,
                "best_affinity_kcal_mol": modes[0]["affinity_kcal_mol"] if modes else None,
                "modes": modes,
                "vina_stdout_tail": stdout[-1500:],
            }
        )

    scored = [x for x in ligand_results if x["best_affinity_kcal_mol"] is not None]
    scored.sort(key=lambda item: item["best_affinity_kcal_mol"])

    versions = {
        "vina": _run(["vina", "--version"]).strip(),
        "meeko": _run(["python", "-c", "import meeko; print(meeko.__version__)"]).strip(),
        "rdkit": _run(["python", "-c", "import rdkit; print(rdkit.__version__)"]).strip(),
    }

    return {
        "summary": {
            "job_id": job_id,
            "receptor": pdb_id,
            "ligand_count": len(ligand_results),
            "best_pubchem_cid": scored[0]["pubchem_cid"] if scored else None,
            "best_affinity_kcal_mol": scored[0]["best_affinity_kcal_mol"] if scored else None,
            "scientific_status": "computational_hypothesis",
        },
        "receptor": receptor_meta,
        "parameters": params,
        "ligand_results": ligand_results,
        "software_versions": versions,
        "integrity": {
            "experimental_validation_required": True,
            "clinical_efficacy_not_established": True,
            "binding_affinity_is_model_output": True,
        },
    }
