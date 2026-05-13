import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Spinner, PageError, StatusBadge } from "../../components/Layout";
import {
  useAdminStats,
  useAdminUsers,
  useChangeUserRole,
  useDeactivateUser,
  useAdminExportStats,
  useAdminTopHerbs,
  useAdminTopMarkets,
  type AdminUser,
  type AdminUsersParams,
} from "../../hooks/useAdmin";
import type { UserRole } from "../../types";

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sub,
  accent = false,
}: {
  icon: string;
  label: string;
  value: number | string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`card flex items-center gap-4 ${
        accent ? "border-forest-300 bg-forest-50" : ""
      }`}
    >
      <div className="w-12 h-12 bg-forest-100 rounded-xl flex items-center justify-center text-2xl shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <div className="text-2xl font-bold text-forest-700">{value}</div>
        <div className="text-sm text-gray-500 leading-tight">{label}</div>
        {sub && <div className="text-xs text-forest-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

// ── Stats Section ──────────────────────────────────────────────────────────────

function StatsSection() {
  const { data: stats, isLoading, error } = useAdminStats();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner />
      </div>
    );
  }
  if (error) return <PageError message="Could not load platform statistics." />;
  if (!stats) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-forest-800 flex items-center gap-2">
        <span>📊</span> Platform Overview
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard icon="👥" label="Total Users" value={stats.total_users} />
        <StatCard
          icon="🌿"
          label="Herbs"
          value={stats.total_herbs}
        />
        <StatCard
          icon="💊"
          label="Formulations"
          value={stats.total_formulations}
          sub={`${stats.published_formulations} published`}
        />
        <StatCard
          icon="🔬"
          label="Trials"
          value={stats.total_trials}
          sub={`${stats.verified_trials} verified`}
        />
        <StatCard
          icon="🌾"
          label="Farm Listings"
          value={stats.total_farm_listings}
          sub={`${stats.active_listings} active`}
        />
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <StatCard
          icon="📋"
          label="Compliance Docs"
          value={stats.total_compliance_docs}
          accent
        />
        <StatCard
          icon="🩺"
          label="Patient Outcomes"
          value={stats.total_patient_outcomes}
          accent
        />
        <StatCard
          icon="✅"
          label="Verified Trials"
          value={stats.verified_trials}
          sub={`of ${stats.total_trials} total`}
          accent
        />
      </div>
    </div>
  );
}

// ── Users Table ────────────────────────────────────────────────────────────────

const ROLES: UserRole[] = ["farmer", "researcher", "pharma_company", "admin"];

function roleLabel(role: UserRole): string {
  return (
    { farmer: "Farmer", researcher: "Researcher", pharma_company: "Pharma Co.", admin: "Admin" }[
      role
    ] ?? role
  );
}

function UserRow({
  user,
  onRoleChange,
  onDeactivate,
  isPending,
}: {
  user: AdminUser;
  onRoleChange: (id: number, role: UserRole) => void;
  onDeactivate: (id: number) => void;
  isPending: boolean;
}) {
  return (
    <tr className="border-b border-gray-100 hover:bg-forest-50 transition-colors">
      <td className="py-3 px-4">
        <div className="font-medium text-gray-800 text-sm">{user.full_name}</div>
        <div className="text-xs text-gray-400">{user.email}</div>
      </td>
      <td className="py-3 px-4">
        <select
          value={user.role}
          disabled={isPending || !user.is_active}
          onChange={(e) => onRoleChange(user.id, e.target.value as UserRole)}
          className="text-sm border border-gray-200 rounded-lg px-2 py-1 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-forest-400 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {roleLabel(r)}
            </option>
          ))}
        </select>
      </td>
      <td className="py-3 px-4">
        <StatusBadge status={user.is_active ? "active" : "withdrawn"} />
      </td>
      <td className="py-3 px-4 text-right">
        {user.is_active ? (
          <button
            onClick={() => onDeactivate(user.id)}
            disabled={isPending}
            className="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            Deactivate
          </button>
        ) : (
          <span className="text-xs text-gray-400 italic">Inactive</span>
        )}
      </td>
    </tr>
  );
}

function UsersSection() {
  const [filters, setFilters] = useState<AdminUsersParams>({
    role: "",
    is_active: "",
    skip: 0,
    limit: 20,
  });

  const { data: users, isLoading, error } = useAdminUsers(filters);
  const { mutate: changeRole, isPending: rolePending } = useChangeUserRole();
  const { mutate: deactivate, isPending: deactivatePending } = useDeactivateUser();

  const isPending = rolePending || deactivatePending;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-bold text-forest-800 flex items-center gap-2">
          <span>👥</span> User Management
        </h2>
        <div className="flex gap-2 flex-wrap">
          {/* Role filter */}
          <select
            value={filters.role ?? ""}
            onChange={(e) =>
              setFilters((f) => ({ ...f, role: e.target.value as UserRole | "", skip: 0 }))
            }
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-forest-400"
          >
            <option value="">All Roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {roleLabel(r)}
              </option>
            ))}
          </select>

          {/* Active filter */}
          <select
            value={filters.is_active === "" ? "" : String(filters.is_active)}
            onChange={(e) =>
              setFilters((f) => ({
                ...f,
                is_active:
                  e.target.value === "" ? "" : e.target.value === "true",
                skip: 0,
              }))
            }
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-forest-400"
          >
            <option value="">All Status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      <div className="card overflow-hidden p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-10">
            <Spinner />
          </div>
        ) : error ? (
          <div className="p-4">
            <PageError message="Could not load users." />
          </div>
        ) : !users || users.length === 0 ? (
          <div className="text-center py-10 text-gray-400 text-sm">
            No users found matching the current filters.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-forest-50 border-b border-forest-100">
                  <th className="text-left py-3 px-4 text-forest-700 font-semibold text-xs uppercase tracking-wide">
                    User
                  </th>
                  <th className="text-left py-3 px-4 text-forest-700 font-semibold text-xs uppercase tracking-wide">
                    Role
                  </th>
                  <th className="text-left py-3 px-4 text-forest-700 font-semibold text-xs uppercase tracking-wide">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 text-forest-700 font-semibold text-xs uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <UserRow
                    key={user.id}
                    user={user}
                    onRoleChange={(id, role) => changeRole({ id, role })}
                    onDeactivate={(id) => deactivate(id)}
                    isPending={isPending}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination controls */}
        {users && users.length > 0 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 bg-gray-50">
            <span className="text-xs text-gray-500">
              Showing {(filters.skip ?? 0) + 1}–
              {(filters.skip ?? 0) + users.length}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    skip: Math.max(0, (f.skip ?? 0) - (f.limit ?? 20)),
                  }))
                }
                disabled={(filters.skip ?? 0) === 0}
                className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-forest-50 hover:border-forest-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                ← Previous
              </button>
              <button
                onClick={() =>
                  setFilters((f) => ({
                    ...f,
                    skip: (f.skip ?? 0) + (f.limit ?? 20),
                  }))
                }
                disabled={users.length < (filters.limit ?? 20)}
                className="text-xs px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-forest-50 hover:border-forest-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Export Stats Section ───────────────────────────────────────────────────────

function ExportKeyValue({ label, value }: { label: string; value: unknown }) {
  if (value === null || value === undefined) return null;
  if (typeof value === "object") return null;
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-600 capitalize">
        {String(label).replace(/_/g, " ")}
      </span>
      <span className="text-sm font-semibold text-forest-700">{String(value)}</span>
    </div>
  );
}

function ExportSection() {
  const {
    data: exportStats,
    isLoading: statsLoading,
    error: statsError,
  } = useAdminExportStats();
  const {
    data: topHerbs,
    isLoading: herbsLoading,
    error: herbsError,
  } = useAdminTopHerbs();
  const {
    data: topMarkets,
    isLoading: marketsLoading,
    error: marketsError,
  } = useAdminTopMarkets();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-bold text-forest-800 flex items-center gap-2">
        <span>🌍</span> Export Engine Analytics
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Engine stats */}
        <div className="card">
          <h3 className="section-title mb-3">Engine Statistics</h3>
          {statsLoading ? (
            <Spinner />
          ) : statsError ? (
            <p className="text-red-500 text-sm">Failed to load.</p>
          ) : exportStats && typeof exportStats === "object" ? (
            <div>
              {Object.entries(exportStats).map(([k, v]) => (
                <ExportKeyValue key={k} label={k} value={v} />
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No data available.</p>
          )}
        </div>

        {/* Top herbs */}
        <div className="card">
          <h3 className="section-title mb-3">Top Herbs by Volume</h3>
          {herbsLoading ? (
            <Spinner />
          ) : herbsError ? (
            <p className="text-red-500 text-sm">Failed to load.</p>
          ) : topHerbs && topHerbs.length > 0 ? (
            <ol className="space-y-2">
              {topHerbs.slice(0, 8).map((herb, i) => {
                const name =
                  (herb as Record<string, unknown>)["name"] ??
                  (herb as Record<string, unknown>)["herb_name"] ??
                  (herb as Record<string, unknown>)["name_english"] ??
                  `Herb ${i + 1}`;
                const vol =
                  (herb as Record<string, unknown>)["volume"] ??
                  (herb as Record<string, unknown>)["total_volume"] ??
                  (herb as Record<string, unknown>)["quantity_kg"];
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="w-5 h-5 bg-forest-100 rounded-full flex items-center justify-center text-xs font-bold text-forest-600 shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700 flex-1 truncate">
                      {String(name)}
                    </span>
                    {vol !== undefined && (
                      <span className="text-xs text-forest-600 font-medium shrink-0">
                        {String(vol)} kg
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="text-gray-400 text-sm">No data available.</p>
          )}
        </div>

        {/* Top markets */}
        <div className="card">
          <h3 className="section-title mb-3">Top Destination Markets</h3>
          {marketsLoading ? (
            <Spinner />
          ) : marketsError ? (
            <p className="text-red-500 text-sm">Failed to load.</p>
          ) : topMarkets && topMarkets.length > 0 ? (
            <ol className="space-y-2">
              {topMarkets.slice(0, 8).map((market, i) => {
                const country =
                  (market as Record<string, unknown>)["country"] ??
                  (market as Record<string, unknown>)["destination"] ??
                  (market as Record<string, unknown>)["market"] ??
                  `Market ${i + 1}`;
                const vol =
                  (market as Record<string, unknown>)["volume"] ??
                  (market as Record<string, unknown>)["total_volume"] ??
                  (market as Record<string, unknown>)["shipment_count"];
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="w-5 h-5 bg-gold-100 rounded-full flex items-center justify-center text-xs font-bold text-gold-600 shrink-0">
                      {i + 1}
                    </span>
                    <span className="text-sm text-gray-700 flex-1 truncate">
                      {String(country)}
                    </span>
                    {vol !== undefined && (
                      <span className="text-xs text-forest-600 font-medium shrink-0">
                        {String(vol)}
                      </span>
                    )}
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="text-gray-400 text-sm">No data available.</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { user } = useAuth();

  // Guard: redirect non-admins
  if (!user) return null;
  if (user.role !== "admin") return <Navigate to="/dashboard" replace />;

  return (
    <div className="space-y-8">
      {/* Header banner */}
      <div className="bg-forest-700 text-white px-6 py-6 rounded-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-forest-200 text-sm">Admin Console</p>
            <h1 className="text-2xl font-bold mt-0.5">NigerFlora BioSciences</h1>
            <p className="text-forest-200 text-sm mt-1">
              Full platform oversight — users, content, exports, and compliance.
            </p>
          </div>
          <div className="flex items-center gap-2 bg-forest-800/60 px-4 py-2 rounded-lg">
            <span className="text-gold-300 text-sm font-semibold">🛡 Admin</span>
            <span className="text-forest-300 text-xs">{user.full_name}</span>
          </div>
        </div>
      </div>

      {/* Platform stats */}
      <StatsSection />

      <hr className="border-forest-100" />

      {/* User management */}
      <UsersSection />

      <hr className="border-forest-100" />

      {/* Export analytics */}
      <ExportSection />
    </div>
  );
}
