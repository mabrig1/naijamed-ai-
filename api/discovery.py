from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

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

COMPOUND_ASSET_FIELDS = {
    "kind",
    "external_id",
    "name",
    "source",
    "source_url",
    "image_url",
    "molecular_formula",
    "molecular_weight",
    "connectivity_smiles",
    "smiles",
    "inchikey",
}

PROTEIN_ASSET_FIELDS = {
    "kind",
    "external_id",
    "name",
    "source",
    "source_url",
    "experimental_method",
    "resolution_angstrom",
    "citation_title",
    "polymer_entity_count",
}


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


def short_text(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


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
    properties = "Title,MolecularFormula,MolecularWeight,ConnectivitySMILES,SMILES,InChIKey"
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
    if not cid:
        raise HTTPException(status_code=502, detail="PubChem response did not include a CID")
    return {
        "kind": "compound",
        "external_id": cid,
        "name": row.get("Title") or value,
        "molecular_formula": row.get("MolecularFormula"),
        "molecular_weight": row.get("MolecularWeight"),
        "connectivity_smiles": row.get("ConnectivitySMILES"),
        "smiles": row.get("SMILES"),
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


def normalize_asset(asset: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    kind = short_text(asset.get("kind"), 20)
    external_id = short_text(asset.get("external_id"), 80)
    if kind not in {"compound", "protein"} or not external_id:
        raise HTTPException(status_code=422, detail="A valid compound or protein asset is required")
    if kind == "protein":
        external_id = external_id.upper()
    allowed = COMPOUND_ASSET_FIELDS if kind == "compound" else PROTEIN_ASSET_FIELDS
    safe_asset = {key: asset.get(key) for key in allowed if asset.get(key) is not None}
    safe_asset["kind"] = kind
    safe_asset["external_id"] = external_id
    safe_asset["name"] = short_text(asset.get("name") or external_id, 320)
    if "source" in safe_asset:
        safe_asset["source"] = short_text(safe_asset["source"], 120)
    if "source_url" in safe_asset:
        safe_asset["source_url"] = short_text(safe_asset["source_url"], 1000)
    if "image_url" in safe_asset:
        safe_asset["image_url"] = short_text(safe_asset["image_url"], 1000)
    return kind, external_id, safe_asset


def normalize_network(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    normalized_nodes: list[dict[str, str]] = []
    node_ids: set[str] = set()
    for node in nodes:
        node_id = short_text(node.get("id"), 80)
        if not node_id or node_id in node_ids:
            continue
        node_ids.add(node_id)
        normalized_nodes.append(
            {
                "id": node_id,
                "label": short_text(node.get("label") or node_id, 240),
                "type": short_text(node.get("type") or "entity", 40),
            }
        )
    if not normalized_nodes:
        raise HTTPException(status_code=422, detail="Add at least one valid network node")

    normalized_edges: list[dict[str, str]] = []
    for edge in edges:
        source = short_text(edge.get("source"), 80)
        target = short_text(edge.get("target"), 80)
        if source not in node_ids or target not in node_ids:
            raise HTTPException(status_code=422, detail="Every network edge must reference existing node ids")
        normalized_edges.append(
            {
                "source": source,
                "target": target,
                "relation": short_text(edge.get("relation") or "associated_with", 120),
                "evidence": short_text(edge.get("evidence"), 1200),
            }
        )
    return normalized_nodes, normalized_edges


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
        kind, external_id, safe_asset = normalize_asset(body.asset or {})
        key = {"user_id": user_id, "kind": kind, "external_id": external_id}
        db.discovery_assets.update_one(
            key,
            {"$set": {**safe_asset, **key, "updated_at": now()}, "$setOnInsert": {"created_at": now()}},
            upsert=True,
        )
        saved = db.discovery_assets.find_one(key)
        if not saved:
            raise HTTPException(status_code=500, detail="Discovery asset could not be saved")
        return {"asset": clean_doc(saved), "message": "Saved to your discovery library."}

    if body.action == "library":
        rows = db.discovery_assets.find({"user_id": user_id}).sort("created_at", -1).limit(500)
        return {"assets": [clean_doc(row) for row in rows]}

    if body.action == "create_screening_job":
        receptor_id = short_text(body.receptor_id, 80).upper()
        ligand_ids = list(dict.fromkeys(short_text(value, 80) for value in body.ligand_ids if short_text(value, 80)))
        if not receptor_id or not ligand_ids:
            raise HTTPException(status_code=422, detail="Choose one saved receptor and at least one saved compound")
        receptor = db.discovery_assets.find_one({"user_id": user_id, "kind": "protein", "external_id": receptor_id})
        ligand_count = db.discovery_assets.count_documents({"user_id": user_id, "kind": "compound", "external_id": {"$in": ligand_ids}})
        if not receptor or ligand_count != len(ligand_ids):
            raise HTTPException(status_code=409, detail="Screening inputs must come from your saved discovery library")
        parameters = normalize_parameters(body.parameters)
        job_id = f"VS-{now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
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
            "title": short_text(body.title or f"Virtual screening against {receptor_id}", 240),
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
        normalized_nodes, normalized_edges = normalize_network(body.nodes, body.edges)
        network_id = f"NET-{now().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        network = {
            "_id": network_id,
            "user_id": user_id,
            "title": short_text(body.title or "Interaction evidence network", 240),
            "nodes": normalized_nodes,
            "edges": normalized_edges,
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
