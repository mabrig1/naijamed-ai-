from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Request
from jose import JWTError, jwt
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.core.mongo import get_db

app = FastAPI(title="NigerFlora Discovery Workbench", version="1.0.0")

HTTP_HEADERS = {
    "User-Agent": "NigerFlora-BioSciences/1.0 research-workbench",
    "Accept": "application/json",
}

SCIENTIFIC_NOTICE = (
    "Database lookups and virtual-screening manifests support hypothesis generation. "
    "They are not experimental validation, clinical evidence, or proof of efficacy or safety."
)


class DiscoveryAction(BaseModel):
    action: str
    query: str | None = Field(default=None, max_length=240)
    asset: dict[str, Any] | None = None
    title: str | None = Field(default=None, max_length=240)
    receptor_id: str | None = Field(default=None, max_length=80)
    ligand_ids: list[str] = Field(default_factory=list, max_length=250)
    parameters: dict[str, Any] = Field(default_factory=dict)
    nodes: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    edges: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)


def now() -> datetime:
    return datetime.now(timezone.utc)


def user_from_request(request: Request) -> dict[str, Any]:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid access token")
    try:
        user_id = ObjectId(str(payload.get("sub")))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid access token")
    user = get_db().users.find_one({"_id": user_id, "is_active": {"$ne": False}})
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if int(payload.get("ver", -1)) != int(user.get("token_version", 0)):
        raise HTTPException(status_code=401, detail="Session expired or revoked")
    return user


def clean_doc(doc: dict[str, Any]) -> dict[str, Any]:
    result = dict(doc)
    result["id"] = str(result.pop("_id"))
    for key, value in list(result.items()):
        if isinstance(value, datetime):
            result[key] = value.isoformat()
    return result


def pubchem_lookup(query_value: str) -> dict[str, Any]:
    value = query_value.strip()
    if not value:
        raise HTTPException(status_code=422, detail="Compound name or CID is required")
    namespace = "cid" if value.isdigit() else "name"
    encoded = quote(value, safe="")
    properties = "Title,MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,InChIKey"
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/{namespace}/{encoded}/property/{properties}/JSON"
    try:
        response = httpx.get(url, headers=HTTP_HEADERS, timeout=20)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Compound not found in PubChem")
        response.raise_for_status()
        rows = response.json().get("PropertyTable", {}).get("Properties", [])
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"PubChem lookup failed: {exc}")
    if not rows:
        raise HTTPException(status_code=404, detail="Compound not found in PubChem")
    row = rows[0]
    cid = str(row.get("CID", ""))
    return {
        "kind": "compound",
        "external_id": cid,
        "name": row.get("Title") or value,
        "molecular_formula": row.get("MolecularFormula"),
        "molecular_weight": row.get("MolecularWeight"),
        "canonical_smiles": row.get("CanonicalSMILES") or row.get("ConnectivitySMILES"),
        "isomeric_smiles": row.get("IsomericSMILES") or row.get("SMILES"),
        "inchikey": row.get("InChIKey"),
        "source": "PubChem",
        "source_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        "image_url": f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG?image_size=large",
    }


def rcsb_lookup(query_value: str) -> dict[str, Any]:
    pdb_id = query_value.strip().upper()
    if len(pdb_id) != 4 or not pdb_id.isalnum():
        raise HTTPException(status_code=422, detail="Enter a valid 4-character PDB ID")
    url = f"https://data.rcsb.org/rest/v1/core/entry/{quote(pdb_id, safe='')}"
    try:
        response = httpx.get(url, headers=HTTP_HEADERS, timeout=20)
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Protein structure not found in RCSB PDB")
        response.raise_for_status()
        data = response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"RCSB PDB lookup failed: {exc}")

    methods = data.get("exptl") or []
    resolution = (data.get("rcsb_entry_info") or {}).get("resolution_combined") or []
    citation = data.get("rcsb_primary_citation") or {}
    return {
        "kind": "protein",
        "external_id": pdb_id,
        "name": (data.get("struct") or {}).get("title") or pdb_id,
        "experimental_method": methods[0].get("method") if methods else None,
        "resolution_angstrom": resolution[0] if resolution else None,
        "citation_title": citation.get("title"),
        "polymer_entity_count": (data.get("rcsb_entry_info") or {}).get("polymer_entity_count"),
        "source": "RCSB Protein Data Bank",
        "source_url": f"https://www.rcsb.org/structure/{pdb_id}",
    }


def normalize_parameters(raw: dict[str, Any]) -> dict[str, Any]:
    def number(name: str, default: float, minimum: float, maximum: float) -> float:
        try:
            value = float(raw.get(name, default))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"{name} must be numeric")
        if not minimum <= value <= maximum:
            raise HTTPException(status_code=422, detail=f"{name} must be between {minimum} and {maximum}")
        return value

    return {
        "center_x": number("center_x", 0, -500, 500),
        "center_y": number("center_y", 0, -500, 500),
        "center_z": number("center_z", 0, -500, 500),
        "size_x": number("size_x", 20, 5, 100),
        "size_y": number("size_y", 20, 5, 100),
        "size_z": number("size_z", 20, 5, 100),
        "exhaustiveness": int(number("exhaustiveness", 8, 1, 64)),
        "num_modes": int(number("num_modes", 9, 1, 50)),
        "seed": int(number("seed", 0, 0, 2_147_483_647)),
    }


@app.get("/api/discovery")
def discovery_info():
    return {
        "name": "NigerFlora Discovery Workbench",
        "capabilities": [
            "PubChem compound lookup",
            "RCSB PDB structure lookup",
            "compound and protein library",
            "AutoDock Vina-compatible screening manifests",
            "interaction-network evidence workspace",
            "reproducibility history and manifest export",
        ],
        "execution_boundary": "Vercel stores and manages reproducible jobs; native docking requires a separate compute worker.",
        "scientific_notice": SCIENTIFIC_NOTICE,
    }


@app.post("/api/discovery")
def discovery_action(body: DiscoveryAction, request: Request):
    user = user_from_request(request)
    user_id = str(user["_id"])
    db = get_db()

    if body.action == "lookup_compound":
        return {"result": pubchem_lookup(body.query or ""), "scientific_notice": SCIENTIFIC_NOTICE}

    if body.action == "lookup_protein":
        return {"result": rcsb_lookup(body.query or ""), "scientific_notice": SCIENTIFIC_NOTICE}

    if body.action == "save_asset":
        asset = body.asset or {}
        kind = str(asset.get("kind", "")).strip()
        external_id = str(asset.get("external_id", "")).strip()
        if kind not in {"compound", "protein"} or not external_id:
            raise HTTPException(status_code=422, detail="A valid compound or protein asset is required")
        safe_asset = {k: v for k, v in asset.items() if k not in {"_id", "user_id", "created_at", "updated_at"}}
        key = {"user_id": user_id, "kind": kind, "external_id": external_id}
        db.discovery_assets.update_one(
            key,
            {"$set": {**safe_asset, **key, "updated_at": now()}, "$setOnInsert": {"created_at": now()}},
            upsert=True,
        )
        saved = db.discovery_assets.find_one(key)
        return {"asset": clean_doc(saved), "message": "Saved to your discovery library."}

    if body.action == "library":
        rows = db.discovery_assets.find({"user_id": user_id}).sort("created_at", -1).limit(500)
        return {"assets": [clean_doc(row) for row in rows]}

    if body.action == "create_screening_job":
        receptor_id = (body.receptor_id or "").strip().upper()
        ligand_ids = list(dict.fromkeys(x.strip() for x in body.ligand_ids if x.strip()))
        if not receptor_id or not ligand_ids:
            raise HTTPException(status_code=422, detail="Choose one saved receptor and at least one saved compound")
        receptor = db.discovery_assets.find_one({"user_id": user_id, "kind": "protein", "external_id": receptor_id})
        ligand_count = db.discovery_assets.count_documents({"user_id": user_id, "kind": "compound", "external_id": {"$in": ligand_ids}})
        if not receptor or ligand_count != len(ligand_ids):
            raise HTTPException(status_code=409, detail="Screening inputs must come from your saved discovery library")
        parameters = normalize_parameters(body.parameters)
        job_id = f"VS-{now().strftime('%Y%m%d%H%M%S')}-{str(user['_id'])[-6:]}"
        manifest = {
            "manifest_version": "1.0",
            "engine": "AutoDock Vina compatible",
            "execution_mode": "external_worker_required",
            "receptor": {"pdb_id": receptor_id, "source": "RCSB PDB"},
            "ligands": [{"pubchem_cid": cid, "source": "PubChem"} for cid in ligand_ids],
            "parameters": parameters,
            "scientific_notice": SCIENTIFIC_NOTICE,
        }
        job = {
            "_id": job_id,
            "user_id": user_id,
            "title": (body.title or f"Virtual screening against {receptor_id}").strip(),
            "status": "ready_for_worker",
            "manifest": manifest,
            "results": None,
            "created_at": now(),
            "updated_at": now(),
        }
        db.discovery_screening_jobs.insert_one(job)
        return {"job": clean_doc(job), "message": "Reproducible screening manifest created. No docking result has been fabricated."}

    if body.action == "my_screening_jobs":
        rows = db.discovery_screening_jobs.find({"user_id": user_id}).sort("created_at", -1).limit(200)
        return {"jobs": [clean_doc(row) for row in rows]}

    if body.action == "save_network":
        if not body.nodes:
            raise HTTPException(status_code=422, detail="Add at least one network node")
        node_ids = {str(node.get("id", "")) for node in body.nodes if node.get("id")}
        if not node_ids:
            raise HTTPException(status_code=422, detail="Each network node needs an id")
        for edge in body.edges:
            if str(edge.get("source", "")) not in node_ids or str(edge.get("target", "")) not in node_ids:
                raise HTTPException(status_code=422, detail="Every network edge must reference existing node ids")
        network_id = f"NET-{now().strftime('%Y%m%d%H%M%S')}-{str(user['_id'])[-6:]}"
        network = {
            "_id": network_id,
            "user_id": user_id,
            "title": (body.title or "Interaction evidence network").strip(),
            "nodes": body.nodes,
            "edges": body.edges,
            "status": "hypothesis_generating",
            "created_at": now(),
            "updated_at": now(),
        }
        db.discovery_networks.insert_one(network)
        return {"network": clean_doc(network), "scientific_notice": SCIENTIFIC_NOTICE}

    if body.action == "my_networks":
        rows = db.discovery_networks.find({"user_id": user_id}).sort("created_at", -1).limit(200)
        return {"networks": [clean_doc(row) for row in rows]}

    raise HTTPException(status_code=400, detail="Unsupported discovery action")
