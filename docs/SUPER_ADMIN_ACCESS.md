# NigerFlora Super Admin — Secure Owner Access

## Scope

The browser console at `/owner` is available only to an authenticated user
whose database role is `super_admin`. It offers module navigation, summarized
statistics, limited account administration and an audit trail.

Normal users and ordinary admins cannot see the owner API, assign themselves
the owner role, or promote other users to Super Admin. The owner console
deliberately excludes production keys, raw clinical records, payment
configuration, passwords and private health data.

## First owner activation: server-side, explicit

1. Confirm the intended owner account already exists and can log in.
2. From an **operator-controlled private terminal** with secure Vercel/Atlas
   environment credentials, set `MONGODB_URI` and `ADMIN_EMAILS` in the
   private process environment. The latter should contain the exact verified
   owner account email (e.g., `victoryonline1@gmail.com`) and must not be
   exposed in a browser or pushed to the repository.
3. Run `python scripts/promote_super_admin.py --email <existing-owner-email>`.
4. Enter that existing account's password using the interactive hidden prompt.
5. Sign out and sign in. The new role appears from `GET /api/auth/me` as
   `super_admin`. Visit `/owner`.

**Do not** automatically grant owner powers to emails entered in a public
registration form, to arbitrary accounts, or merely because a user's email
matches an allowlist. The bootstrap never creates a user and never changes a
password. It records an audit event and revokes existing sessions via
`token_version`.

## Administration safeguards

- All `/api/owner/*` endpoints require the database-backed role.
- Owner changes to other accounts invalidate their existing access tokens.
- Role assignment can grant `admin` but not `super_admin`.
- A Super Admin cannot deactivate themselves or another Super Admin through
  the browser.
- User lists contain no password hashes, session tokens, or clinical records.
- Clinical/medical content maintains independent access and audit rules.
- No payment configuration, provider keys, cloud permissions or DNS is touched.

Run tests before rollout:

    python -m unittest discover -s tests -p "test_super_admin_security.py" -v
    npm ci --prefix frontend
    npm run build --prefix frontend

The owner console becomes usable only after the feature PR is merged,
deployed and the existing account is manually promoted. Do not claim access
has been granted until those steps have been verified.
