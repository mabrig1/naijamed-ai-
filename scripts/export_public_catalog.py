"""Export a read-only public catalog snapshot from API literals without importing the backend.

Run: python scripts/export_public_catalog.py
Check CI drift: python scripts/export_public_catalog.py --check
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "api" / "research_commerce.py"
DEST = ROOT / "frontend" / "src" / "generated" / "bioinformatics-catalog.json"


def extract_literals() -> dict:
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    values = {}
    targets = {"SERVICE_CATALOG", "ADD_ONS", "INTEGRITY_NOTICE", "ORDER_STATUSES"}
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name, value = node.target.id, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        else:
            continue
        if name in targets:
            values[name] = ast.literal_eval(value)
    if set(values) != targets:
        raise ValueError("Missing catalog source literals: " + str(sorted(targets - set(values))))
    return values


def generate() -> str:
    values = extract_literals()
    payload = {
        "studio": "NigerFlora BioSciences — Bioinformatics Consulting & Data Analysis",
        "services": values["SERVICE_CATALOG"],
        "addons": values["ADD_ONS"],
        "markets": [
            {"id": "local", "name": "Nigeria / Local", "currency": "NGN", "recommended_gateway": "paystack"},
            {"id": "global", "name": "International", "currency": "USD", "recommended_gateway": "flutterwave"},
        ],
        "gateways": ["paystack", "flutterwave"],
        "order_statuses": values["ORDER_STATUSES"],
        "integrity_notice": values["INTEGRITY_NOTICE"],
        "catalog_mode": "reference",
        "checkout_available": False,
    }
    if not payload["services"] or any(not item.get("tiers") for item in payload["services"]):
        raise ValueError("Invalid or empty public services catalog")
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail when snapshot needs regeneration")
    args = parser.parse_args()
    expected = generate()
    if args.check:
        if not DEST.exists() or DEST.read_text(encoding="utf-8") != expected:
            raise SystemExit("Public catalog snapshot is stale: run python scripts/export_public_catalog.py")
        print("Public catalog snapshot is up to date")
        return
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(expected, encoding="utf-8")
    print("Wrote " + str(DEST.relative_to(ROOT)))


if __name__ == "__main__":
    main()
