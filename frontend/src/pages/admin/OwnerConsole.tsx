import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { PageError, Spinner } from "../../components/Layout";

type OwnerUser = { id: string; email: string; full_name: string; role: string; is_active: boolean };
type Module = { path: string; name: string };
type Overview = {
  modules: Module[];
  users_total: number;
  users_active: number;
  discovery_assets: number;
  research_projects: number;
  service_orders: number;
  payments_enabled_by_console: boolean;
};
const roles = ["patient", "doctor", "clinic", "hmo", "researcher", "farmer", "pharma_company", "admin"];
function problem(error: unknown) {
  const detail = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
  return detail || "The owner service is unavailable. Verify the MongoDB connection and your Super Admin role.";
}

export default function OwnerConsole() {
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [users, setUsers] = useState<OwnerUser[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState("");
  const [pendingRoles, setPendingRoles] = useState<Record<string, string>>({});

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const [a, b] = await Promise.all([
        api.get<Overview>("/api/owner/overview"),
        api.get<{ users: OwnerUser[] }>("/api/owner/users"),
      ]);
      setOverview(a.data);
      setUsers(b.data.users);
      setPendingRoles(Object.fromEntries(b.data.users.map(u => [u.id, u.role])));
    } catch (e) {
      setError(problem(e));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { if (user?.role === "super_admin") void refresh(); }, [user?.role]);

  async function updateAccount(id: string, change: { role?: string; is_active?: boolean }) {
    setEditing(id);
    setError("");
    setSuccess("");
    try {
      await api.patch("/api/owner/users/" + encodeURIComponent(id), change);
      setSuccess("Account updated. Its existing sessions were revoked.");
      await refresh();
    } catch (e) {
      setError(problem(e));
    } finally {
      setEditing("");
    }
  }

  if (user?.role !== "super_admin") {
    return <PageError message="Verified Super Admin permissions are required. An owner email address alone cannot unlock this console." />;
  }

  return (
    <div className="space-y-7">
      <section className="rounded-3xl bg-forest-800 p-7 text-white">
        <div className="text-xs font-semibold uppercase tracking-widest text-gold-300">NigerFlora owner control center</div>
        <h1 className="mt-2 text-3xl font-bold">Super Admin Console</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-forest-100">
          Access research, discovery, scientific data, commerce oversight and account administration from one authenticated workspace.
          Payment configuration is deliberately outside this console until the application is validated.
        </p>
        <button type="button" className="btn-secondary mt-5" onClick={() => void refresh()} disabled={busy}>
          {busy ? "Refreshing…" : "Refresh system overview"}
        </button>
      </section>

      {error && <PageError message={error} />}
      {success && <div role="status" className="rounded-xl border border-forest-200 bg-forest-50 p-3 text-sm text-forest-800">{success}</div>}

      {overview ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            {[
              ["Total users", overview.users_total],
              ["Active accounts", overview.users_active],
              ["Discovery records", overview.discovery_assets],
              ["Research projects", overview.research_projects],
              ["Service orders", overview.service_orders],
            ].map(([name, total]) => (
              <div key={name} className="card">
                <div className="text-sm text-gray-500">{name}</div>
                <div className="mt-2 text-3xl font-bold text-forest-800">{total}</div>
              </div>
            ))}
          </section>
          <section className="card">
            <h2 className="text-xl font-bold text-forest-800">Application modules</h2>
            <p className="mt-1 text-sm text-gray-500">Use each module under its normal safety, authorization and data-access rules.</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {overview.modules.map(m => (
                <Link className="rounded-xl border border-forest-100 bg-white p-4 text-sm font-semibold text-forest-800 hover:bg-forest-50" key={m.path} to={m.path}>
                  {m.name}
                </Link>
              ))}
            </div>
          </section>
        </>
      ) : busy ? <div className="card flex gap-3"><Spinner /> Loading owner overview…</div> : null}

      <section className="card">
        <h2 className="text-xl font-bold text-forest-800">User and administrator management</h2>
        <p className="mt-2 text-sm text-gray-500">
          Changes are recorded in an audit log and revoke existing sessions. You cannot change your own account,
          change another Super Admin or grant Super Admin privileges through this console.
        </p>
        <div className="mt-5 overflow-x-auto">
          <table className="min-w-[700px] w-full text-left text-sm">
            <thead><tr className="border-b text-gray-500"><th className="py-3 pr-3">Account</th><th className="pr-3">Role</th><th className="pr-3">Status</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className="border-b align-middle">
                  <td className="py-3 pr-3">
                    <div className="font-semibold">{u.full_name}</div>
                    <div className="text-xs text-gray-500">{u.email}</div>
                  </td>
                  <td className="pr-3">
                    {u.role === "super_admin" ? <span className="font-semibold">Super Admin (protected)</span> : (
                      <select aria-label={"Role for " + u.email} className="input max-w-48"
                        value={pendingRoles[u.id] || u.role}
                        onChange={e => setPendingRoles(p => ({ ...p, [u.id]: e.target.value }))}>
                        {roles.map(role => <option value={role} key={role}>{role}</option>)}
                      </select>
                    )}
                  </td>
                  <td className="pr-3">{u.is_active ? "Active" : "Disabled"}</td>
                  <td className="space-x-2 whitespace-nowrap">
                    {u.role !== "super_admin" && (
                      <>
                        <button className="btn-secondary" disabled={editing === u.id || pendingRoles[u.id] === u.role}
                          onClick={() => void updateAccount(u.id, { role: pendingRoles[u.id] })}>Save role</button>
                        <button className="btn-outline" disabled={editing === u.id}
                          onClick={() => { if (window.confirm((u.is_active ? "Disable" : "Activate") + " this account?")) void updateAccount(u.id, { is_active: !u.is_active }); }}>
                          {u.is_active ? "Disable" : "Activate"}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!users.length && !busy && <p className="mt-4 text-sm text-gray-500">No user records available.</p>}
      </section>
      <p className="text-sm text-gray-500">
        Clinical and sensitive records remain subject to consent, confidentiality and scoped access. This console does not bypass those safeguards.
      </p>
    </div>
  );
}
