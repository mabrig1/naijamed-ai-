"""One-time, operator-controlled Super Admin promotion.

Requires production MongoDB credentials and ADMIN_EMAILS in a trusted
private terminal. It never grants privileges via public registration.
The operator must know the user's EXISTING password, proving possession
of that account. Does not create accounts or change passwords.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import settings
from app.core.mongo import get_db
from passlib.context import CryptContext
from datetime import datetime, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def promote(email: str, password: str) -> bool:
    normalized = email.strip().lower()
    allowed = {value.strip().lower() for value in settings.ADMIN_EMAILS.split(",") if value.strip()}
    if not normalized or normalized not in allowed:
        raise ValueError("Email must match the ADMIN_EMAILS owner allowlist")
    if not settings.MONGODB_URI:
        raise RuntimeError("MONGODB_URI must be configured in a trusted operator environment")
    db = get_db()
    account = db.users.find_one({"email": normalized})
    if not account or not account.get("is_active", True):
        raise ValueError("Active existing user account required")
    if not pwd_context.verify(password, account.get("password_hash", "")):
        raise ValueError("Existing account password verification failed")
    if account.get("role") == "super_admin":
        return False
    result = db.users.update_one(
        {"_id": account["_id"], "is_active": {"$ne": False}},
        {"$set": {"role": "super_admin"}, "$inc": {"token_version": 1}},
    )
    if result.modified_count != 1:
        raise RuntimeError("Account not updated")
    db.admin_audit_logs.insert_one({
        "actor_id": str(account["_id"]),
        "target_id": str(account["_id"]),
        "action": "owner.bootstrap",
        "before": {"role": account.get("role")},
        "after": {"role": "super_admin"},
        "created_at": datetime.now(timezone.utc),
    })
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote an existing, password-verified owner account")
    parser.add_argument("--email", required=True, help="Exact email already included in ADMIN_EMAILS")
    args = parser.parse_args()
    password = getpass.getpass("Confirm the account's existing password: ")
    try:
        changed = promote(args.email, password)
    except (ValueError, RuntimeError) as exc:
        print("Owner bootstrap refused:", exc)
        return 1
    print("Super Admin role verified." if not changed else "Super Admin role assigned; re-login required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
