"""Security contracts for owner-only NigerFlora operations."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from api import index

app = index.app


class OwnerSecurityTests(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_unprivileged_roles_cannot_see_owner_console_data(self):
        for role in ("patient", "researcher", "doctor", "admin"):
            with self.subTest(role=role):
                app.dependency_overrides[index.current_user] = lambda role=role: {
                    "_id": "507f1f77bcf86cd799439011",
                    "role": role, "is_active": True,
                }
                with patch.object(index, "get_db", side_effect=AssertionError("No DB for rejected request")):
                    response = TestClient(app).get("/api/owner/overview")
                self.assertEqual(response.status_code, 403)
        app.dependency_overrides.clear()
        response = TestClient(app).get("/api/owner/overview")
        self.assertEqual(response.status_code, 401)

    def test_admin_allowlist_does_not_grant_role_on_registration(self):
        from bson import ObjectId
        account_db = Mock()
        account_db.users.insert_one.return_value = SimpleNamespace(inserted_id=ObjectId())
        with patch.object(index, "get_db", return_value=account_db), patch.object(index.settings, "ADMIN_EMAILS", "owner@example.com"):
            response = TestClient(app).post("/api/auth/register", json={
                "email": "owner@example.com", "full_name": "Test Owner",
                "password": "strongtest123", "role": "patient",
            })
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["role"], "patient")
        inserted = account_db.users.insert_one.call_args.args[0]
        self.assertEqual(inserted["role"], "patient")

    def test_super_admin_registration_is_never_public(self):
        response = TestClient(app).post("/api/auth/register", json={
            "email": "hello@example.com", "full_name": "Example",
            "password": "strongtest123", "role": "super_admin",
        })
        self.assertEqual(response.status_code, 422)

    def test_super_admin_can_list_users_without_secret_fields(self):
        from bson import ObjectId
        account = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "role": "super_admin", "is_active": True,
        }
        app.dependency_overrides[index.current_user] = lambda: account
        db = Mock()
        row = {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "email": "member@example.com", "full_name": "Member",
            "role": "researcher", "is_active": True,
            "password_hash": "SECRET_HASH", "token_version": 7,
        }
        db.users.find.return_value.sort.return_value.limit.return_value = [row]
        with patch.object(index, "get_db", return_value=db):
            response = TestClient(app).get("/api/owner/users")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["users"]), 1)
        self.assertNotIn("password_hash", response.text)
        self.assertNotIn("token_version", response.text)
        self.assertNotIn("SECRET_HASH", response.text)

    def test_owner_role_change_is_audited_and_revokes_existing_sessions(self):
        from bson import ObjectId
        actor = {"_id": ObjectId("507f1f77bcf86cd799439011"), "role": "super_admin"}
        target_id = ObjectId("507f1f77bcf86cd799439012")
        app.dependency_overrides[index.current_user] = lambda: actor
        db = Mock()
        db.users.find_one.side_effect = [
            {"_id": target_id, "role": "researcher", "email": "member@example.com",
             "full_name": "Member", "is_active": True},
            {"_id": target_id, "role": "admin", "email": "member@example.com",
             "full_name": "Member", "is_active": True},
        ]
        db.users.update_one.return_value.matched_count = 1
        with patch.object(index, "get_db", return_value=db):
            response = TestClient(app).patch(
                "/api/owner/users/507f1f77bcf86cd799439012",
                json={"role": "admin"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["user"]["role"], "admin")
        self.assertTrue(response.json()["sessions_revoked"])
        update = db.users.update_one.call_args.args[1]
        self.assertEqual(update["$inc"]["token_version"], 1)
        self.assertEqual(update["$set"]["role"], "admin")
        audit = db.admin_audit_logs.insert_one.call_args.args[0]
        self.assertEqual(audit["action"], "owner.user_update")
        self.assertEqual(audit["before"]["role"], "researcher")
        self.assertEqual(audit["after"]["role"], "admin")

    def test_owner_cannot_promote_self_or_other_owners(self):
        from bson import ObjectId
        account = {"_id": ObjectId("507f1f77bcf86cd799439011"), "role": "super_admin"}
        app.dependency_overrides[index.current_user] = lambda: account
        db = Mock()
        db.users.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439012"), "role": "super_admin",
        }
        with patch.object(index, "get_db", return_value=db):
            own = TestClient(app).patch("/api/owner/users/507f1f77bcf86cd799439011", json={"is_active": False})
            other = TestClient(app).patch("/api/owner/users/507f1f77bcf86cd799439012", json={"is_active": False})
        self.assertEqual(own.status_code, 403)
        self.assertEqual(other.status_code, 403)
        db.users.update_one.assert_not_called()


if __name__ == "__main__":
    unittest.main()
