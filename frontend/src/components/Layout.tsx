import { useState } from "react";
import { Link, NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import type { UserRole } from "../types";

// ── Helpers ──────────────────────────────────────────────────────────────────

function roleLabel(role: UserRole): string {
  return { farmer: "Farmer", researcher: "Researcher", pharma_company: "Pharma", admin: "Admin" }[role] ?? role;
}

interface NavItem { to: string; label: string; roles?: UserRole[] }

const NAV: NavItem[] = [
  { to: "/herbs",        label: "🌿 Herbs" },
  { to: "/formulations", label: "🔬 Formulations", roles: ["researcher","pharma_company","admin"] },
  { to: "/farming",      label: "🌾 Marketplace" },
  { to: "/research",     label: "📊 Research",    roles: ["researcher","admin"] },
  { to: "/compliance",   label: "📋 Compliance",  roles: ["pharma_company","researcher","admin"] },
];

// ── Reusable UI ───────────────────────────────────────────────────────────────

export function Spinner({ className = "" }: { className?: string }) {
  return <span className={`spinner ${className}`} />;
}

export function PageError({ message }: { message: string }) {
  return (
    <div className="card border-red-200 text-red-700 flex items-center gap-3">
      <span className="text-xl">⚠️</span>
      <p>{message}</p>
    </div>
  );
}

export function Empty({ icon = "📭", title = "Nothing here yet", subtitle = "" }: {
  icon?: string; title?: string; subtitle?: string;
}) {
  return (
    <div className="card text-center py-12">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-600">{title}</h3>
      {subtitle && <p className="text-gray-400 mt-1 text-sm">{subtitle}</p>}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft: "badge-gray", submitted: "badge-blue", approved: "badge-green",
    rejected: "badge-red", active: "badge-green", completed: "badge-gold",
    withdrawn: "badge-gray", high: "badge-red", medium: "badge-gold", low: "badge-gray",
  };
  return <span className={map[status] ?? "badge-gray"}>{status}</span>;
}

export function ProgressBar({ value, max = 100, label }: { value: number; max?: number; label?: string }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = pct >= 70 ? "bg-forest-500" : pct >= 40 ? "bg-gold-400" : "bg-earth-400";
  return (
    <div>
      {label && (
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>{label}</span><span>{pct}%</span>
        </div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div className={`${color} h-2.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Main Layout ───────────────────────────────────────────────────────────────

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const visibleNav = NAV.filter(
    (n) => !n.roles || (user && n.roles.includes(user.role))
  );

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      {/* Top navbar */}
      <nav className="bg-forest-600 text-white shadow-lg sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0">
              <span className="text-2xl">🌿</span>
              <div className="leading-tight">
                <div className="font-bold text-lg text-gold-300 tracking-wide">NaijaMed AI</div>
                <div className="text-xs text-forest-200 hidden sm:block">From Soil to Science</div>
              </div>
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {visibleNav.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-forest-700 text-gold-300"
                        : "text-forest-100 hover:bg-forest-500 hover:text-white"
                    }`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </div>

            {/* User menu */}
            <div className="flex items-center gap-3">
              {user && (
                <div className="relative">
                  <button
                    onClick={() => setUserMenuOpen((v) => !v)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-forest-500 transition-colors"
                  >
                    <div className="w-8 h-8 bg-gold-400 rounded-full flex items-center justify-center text-forest-900 font-bold text-sm">
                      {user.full_name.charAt(0).toUpperCase()}
                    </div>
                    <div className="hidden sm:block text-left">
                      <div className="text-sm font-medium">{user.full_name.split(" ")[0]}</div>
                      <div className="text-xs text-forest-300">{roleLabel(user.role)}</div>
                    </div>
                    <span className="text-forest-300 text-xs">▾</span>
                  </button>

                  {userMenuOpen && (
                    <div
                      className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-xl border border-forest-100 py-2 z-50"
                      onBlur={() => setUserMenuOpen(false)}
                    >
                      <div className="px-4 py-2 border-b border-gray-100">
                        <div className="font-semibold text-gray-900 text-sm">{user.full_name}</div>
                        <div className="text-xs text-gray-500">{user.email}</div>
                      </div>
                      <Link to="/dashboard" onClick={() => setUserMenuOpen(false)}
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-forest-50 hover:text-forest-700">
                        📊 Dashboard
                      </Link>
                      <button onClick={handleLogout}
                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                        🚪 Sign out
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Mobile hamburger */}
              <button
                className="md:hidden p-2 rounded-md text-forest-200 hover:text-white hover:bg-forest-500"
                onClick={() => setMobileOpen((v) => !v)}
              >
                <span className="text-xl">{mobileOpen ? "✕" : "☰"}</span>
              </button>
            </div>
          </div>
        </div>

        {/* Mobile nav */}
        {mobileOpen && (
          <div className="md:hidden bg-forest-700 border-t border-forest-500 px-4 pb-4 pt-2 space-y-1">
            {visibleNav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `block px-3 py-2 rounded-md text-sm font-medium ${
                    isActive ? "bg-forest-800 text-gold-300" : "text-forest-100 hover:bg-forest-600"
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
            <hr className="border-forest-600 my-2" />
            <button onClick={handleLogout} className="w-full text-left px-3 py-2 text-sm text-red-300 hover:bg-forest-600 rounded-md">
              🚪 Sign out
            </button>
          </div>
        )}
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-forest-800 text-forest-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-2xl">🌿</span>
                <span className="font-bold text-gold-300 text-lg">NaijaMed AI</span>
              </div>
              <p className="text-sm text-forest-300 leading-relaxed">
                Bridging Nigerian herbal knowledge and pharmaceutical science.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-3">Platform</h4>
              <ul className="space-y-1.5 text-sm">
                {[["Herb Database","/herbs"],["Marketplace","/farming"],["Research Hub","/research"],["NAFDAC Compliance","/compliance"]].map(([l,h]) => (
                  <li key={h}><Link to={h} className="hover:text-gold-300 transition-colors">{l}</Link></li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-white mb-3">Regulatory Notice</h4>
              <p className="text-xs text-forest-400 leading-relaxed">
                AI-generated guidance is informational only. Always consult a certified NAFDAC regulatory consultant before making compliance decisions.
              </p>
            </div>
          </div>
          <div className="border-t border-forest-700 mt-6 pt-4 text-center text-xs text-forest-400">
            © {new Date().getFullYear()} NaijaMed AI · Empowering Nigerian Herbal Medicine
          </div>
        </div>
      </footer>
    </div>
  );
}
