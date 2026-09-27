import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

interface NavItem {
  to: string;
  label: string;
}

const PRIMARY_NAV: NavItem[] = [
  { to: "/bioinformatics-services", label: "💼 Bioinformatics" },
  { to: "/discovery", label: "🧪 Discovery" },
  { to: "/research-studio", label: "🧬 Research Studio" },
  { to: "/formulary", label: "📚 Formulary" },
  { to: "/research", label: "📊 Research" },
  { to: "/herbs", label: "🌿 Herb Data" },
  { to: "/formulations", label: "🔬 Formulations" },
  { to: "/compliance", label: "📋 Compliance" },
];

const BUSINESS_TOOLS: NavItem[] = [
  { to: "/farming", label: "🌾 Marketplace" },
  { to: "/export", label: "🌍 Export" },
  { to: "/prices", label: "📈 Price Intelligence" },
  { to: "/logistics/freight", label: "🚢 Freight" },
  { to: "/customs", label: "🛃 Customs" },
  { to: "/escrow", label: "🔒 Escrow" },
];

function humanRole(role: string): string {
  const labels: Record<string, string> = {
    patient: "Individual",
    researcher: "Researcher",
    doctor: "Doctor",
    clinic: "Clinic",
    hmo: "HMO",
    admin: "Admin",
    farmer: "Farmer",
    pharma_company: "Pharma",
  };
  return labels[role] ?? role;
}

export function Spinner({ className = "" }: { className?: string }) {
  return <span className={`spinner ${className}`} />;
}

export function PageError({ message }: { message: string }) {
  return (
    <div className="card flex items-center gap-3 border-red-200 text-red-700">
      <span className="text-xl">⚠️</span>
      <p>{message}</p>
    </div>
  );
}

export function Empty({ icon = "📭", title = "Nothing here yet", subtitle = "" }: {
  icon?: string;
  title?: string;
  subtitle?: string;
}) {
  return (
    <div className="card py-12 text-center">
      <div className="mb-4 text-5xl">{icon}</div>
      <h3 className="text-lg font-semibold text-gray-600">{title}</h3>
      {subtitle && <p className="mt-1 text-sm text-gray-400">{subtitle}</p>}
    </div>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft: "badge-gray",
    submitted: "badge-blue",
    approved: "badge-green",
    rejected: "badge-red",
    active: "badge-green",
    completed: "badge-gold",
    withdrawn: "badge-gray",
    high: "badge-red",
    medium: "badge-gold",
    low: "badge-gray",
    pending: "badge-gray",
    paid: "badge-green",
    awaiting_payment: "badge-gray",
    intake: "badge-blue",
    queued: "badge-blue",
    running: "badge-gold",
    review: "badge-gold",
    delivered: "badge-green",
    revision: "badge-blue",
    closed: "badge-gray",
    ready_for_worker: "badge-blue",
    hypothesis_generating: "badge-gold",
  };
  return <span className={map[status] ?? "badge-gray"}>{status.split("_").join(" ")}</span>;
}

export function ProgressBar({ value, max = 100, label }: { value: number; max?: number; label?: string }) {
  const pct = Math.min(100, Math.round((value / max) * 100));
  const color = pct >= 70 ? "bg-forest-500" : pct >= 40 ? "bg-gold-400" : "bg-earth-400";
  return (
    <div>
      {label && (
        <div className="mb-1 flex justify-between text-sm text-gray-600">
          <span>{label}</span><span>{pct}%</span>
        </div>
      )}
      <div className="h-2.5 w-full rounded-full bg-gray-200">
        <div className={`${color} h-2.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);
  const toolsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function closeMenus(event: MouseEvent) {
      const node = event.target as Node;
      if (userRef.current && !userRef.current.contains(node)) setUserOpen(false);
      if (toolsRef.current && !toolsRef.current.contains(node)) setToolsOpen(false);
    }
    document.addEventListener("mousedown", closeMenus);
    return () => document.removeEventListener("mousedown", closeMenus);
  }, []);

  function handleLogout() {
    logout();
    navigate("/");
  }

  const navClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
      isActive ? "bg-forest-800 text-gold-300" : "text-forest-100 hover:bg-forest-500 hover:text-white"
    }`;

  return (
    <div className="flex min-h-screen flex-col bg-cream">
      <nav className="sticky top-0 z-50 bg-forest-700 text-white shadow-lg">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between gap-4">
            <Link to="/dashboard" className="flex shrink-0 items-center gap-2.5">
              <span className="text-2xl">🌿</span>
              <div className="leading-tight">
                <div className="text-lg font-bold tracking-wide text-gold-300">NigerFlora BioSciences</div>
                <div className="hidden text-[11px] text-forest-200 sm:block">Care · Research · Discovery</div>
              </div>
            </Link>

            <div className="hidden items-center gap-1 xl:flex">
              {PRIMARY_NAV.map((item) => (
                <NavLink key={item.to} to={item.to} className={navClass}>{item.label}</NavLink>
              ))}
              <div className="relative" ref={toolsRef}>
                <button
                  type="button"
                  onClick={() => setToolsOpen((value) => !value)}
                  className="rounded-md px-3 py-2 text-sm font-medium text-forest-100 hover:bg-forest-500 hover:text-white"
                >
                  Business Tools ▾
                </button>
                {toolsOpen && (
                  <div className="absolute right-0 mt-2 w-64 rounded-2xl border border-forest-100 bg-white p-2 text-gray-800 shadow-2xl">
                    {BUSINESS_TOOLS.map((item) => (
                      <Link key={item.to} to={item.to} onClick={() => setToolsOpen(false)} className="block rounded-xl px-3 py-2.5 text-sm hover:bg-forest-50 hover:text-forest-700">
                        {item.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center gap-2">
              {user && (
                <div className="relative" ref={userRef}>
                  <button type="button" onClick={() => setUserOpen((value) => !value)} className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-forest-500">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gold-400 text-sm font-bold text-forest-900">{user.full_name.charAt(0).toUpperCase()}</div>
                    <div className="hidden text-left sm:block">
                      <div className="text-sm font-medium">{user.full_name.split(" ")[0]}</div>
                      <div className="text-xs text-forest-300">{humanRole(String(user.role))}</div>
                    </div>
                    <span className="text-xs text-forest-300">▾</span>
                  </button>
                  {userOpen && (
                    <div className="absolute right-0 mt-2 w-64 rounded-xl border border-forest-100 bg-white py-2 text-gray-800 shadow-xl">
                      <div className="border-b border-gray-100 px-4 py-2">
                        <div className="text-sm font-semibold">{user.full_name}</div>
                        <div className="truncate text-xs text-gray-500">{user.email}</div>
                      </div>
                      <Link to="/pricing" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm font-semibold text-forest-700 hover:bg-forest-50">💳 Plans & Billing</Link>
                      <Link to="/bioinformatics-services" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm font-semibold text-forest-700 hover:bg-forest-50">💼 Order Bioinformatics Analysis</Link>
                      <Link to="/discovery" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">🧪 Discovery Workbench</Link>
                      <Link to="/formulary" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">📚 Formulary Workspace</Link>
                      <Link to="/formulary/portfolio" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">🎓 Research & Residency Portfolio</Link>
                      <Link to="/formulary/copilot" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">🧾 Regulatory & Grant Copilot</Link>
                      <Link to="/formulary/journal" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">🗣️ Journal Club Live Room</Link>
                      <Link to="/research-studio" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">🧬 Research Studio</Link>
                      {String(user.role) === "admin" && <>
                        <Link to="/monetization/admin" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">📈 Monetization Dashboard</Link>
                        <Link to="/research-commerce/admin" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">💰 Research Commerce Admin</Link>
                      </>}
                      <Link to="/dashboard" onClick={() => setUserOpen(false)} className="block px-4 py-2 text-sm hover:bg-forest-50">📊 Dashboard</Link>
                      <button type="button" onClick={handleLogout} className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50">🚪 Sign out</button>
                    </div>
                  )}
                </div>
              )}
              <button type="button" onClick={() => setMobileOpen((value) => !value)} className="rounded-md p-2 text-forest-100 hover:bg-forest-500 xl:hidden" aria-label="Toggle navigation">
                <span className="text-xl">{mobileOpen ? "✕" : "☰"}</span>
              </button>
            </div>
          </div>
        </div>

        {mobileOpen && (
          <div className="border-t border-forest-600 bg-forest-800 px-4 pb-4 pt-2 xl:hidden">
            <div className="grid gap-1 sm:grid-cols-2">
              {[...PRIMARY_NAV, ...BUSINESS_TOOLS].map((item) => (
                <NavLink key={item.to} to={item.to} onClick={() => setMobileOpen(false)} className={({ isActive }) => `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-forest-900 text-gold-300" : "text-forest-100 hover:bg-forest-700"}`}>
                  {item.label}
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </nav>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8"><Outlet /></main>

      <footer className="mt-auto bg-forest-900 text-forest-200">
        <div className="mx-auto grid max-w-7xl gap-8 px-4 py-9 md:grid-cols-4">
          <div>
            <div className="text-lg font-bold text-gold-300">NigerFlora BioSciences</div>
            <p className="mt-2 text-sm leading-6 text-forest-300">Nigerian healthcare intelligence, ethnobotanical research and computational discovery built for responsible innovation.</p>
          </div>
          <div>
            <h4 className="font-semibold text-white">Research Revenue</h4>
            <div className="mt-3 space-y-2 text-sm">
              <Link className="block font-semibold text-gold-300 hover:text-white" to="/pricing">Plans & Pricing</Link>
              <Link className="block hover:text-gold-300" to="/bioinformatics-services">Order Bioinformatics Services</Link>
              <Link className="block hover:text-gold-300" to="/research-studio">Research Studio</Link>
              <Link className="block hover:text-gold-300" to="/research-studio">Grant & Proposal Support</Link>
            </div>
          </div>
          <div>
            <h4 className="font-semibold text-white">Discovery Pipeline</h4>
            <div className="mt-3 space-y-2 text-sm">
              <Link className="block hover:text-gold-300" to="/discovery">Discovery Workbench</Link>
              <Link className="block hover:text-gold-300" to="/herbs">Herb Data</Link>
              <Link className="block hover:text-gold-300" to="/formulations">Formulations</Link>
              <Link className="block hover:text-gold-300" to="/compliance">Regulatory Tools</Link>
            </div>
          </div>
          <div>
            <h4 className="font-semibold text-white">Scientific Notice</h4>
            <p className="mt-3 text-xs leading-5 text-forest-400">In-silico outputs are hypothesis-generating research evidence. They do not establish clinical efficacy, safety, patentability or regulatory approval without appropriate experimental and professional review.</p>
          </div>
        </div>
        <div className="border-t border-forest-800 px-4 py-4 text-center text-xs text-forest-400">© {new Date().getFullYear()} NigerFlora BioSciences · Powered by MABRIG Technologies</div>
      </footer>
    </div>
  );
}
