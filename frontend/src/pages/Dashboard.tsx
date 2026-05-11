import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useHerbList } from "../hooks/useHerbs";
import { useMyListings } from "../hooks/useFarming";
import { useTrialList } from "../hooks/useResearch";
import { useFormulationList } from "../hooks/useFormulations";
import { useComplianceDocuments } from "../hooks/useCompliance";
import { Spinner, StatusBadge } from "../components/Layout";

function StatCard({ icon, label, value, to }: { icon: string; label: string; value: number | string; to: string }) {
  return (
    <Link to={to} className="card-hover flex items-center gap-4">
      <div className="w-12 h-12 bg-forest-100 rounded-xl flex items-center justify-center text-2xl shrink-0">{icon}</div>
      <div>
        <div className="text-2xl font-bold text-forest-700">{value}</div>
        <div className="text-sm text-gray-500">{label}</div>
      </div>
    </Link>
  );
}

function QuickAction({ icon, label, to }: { icon: string; label: string; to: string }) {
  return (
    <Link to={to} className="flex items-center gap-3 p-4 rounded-xl border border-forest-100 hover:bg-forest-50 hover:border-forest-300 transition-all group">
      <span className="text-2xl group-hover:scale-110 transition-transform">{icon}</span>
      <span className="text-sm font-medium text-forest-700">{label}</span>
      <span className="ml-auto text-forest-400">→</span>
    </Link>
  );
}

function FarmerDashboard() {
  const { data: listings, isLoading } = useMyListings();
  const { data: herbs } = useHerbList({ limit: 5 });
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon="🌾" label="My Listings" value={isLoading ? "…" : (listings?.length ?? 0)} to="/farming" />
        <StatCard icon="🌿" label="Herbs Available" value={herbs?.length ?? "…"} to="/herbs" />
        <StatCard icon="✅" label="Active Listings" value={listings?.filter(l => l.is_available).length ?? 0} to="/farming" />
        <StatCard icon="📈" label="Market Demand" value="View" to="/farming/demand" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction icon="➕" label="Create New Listing" to="/farming/create" />
            <QuickAction icon="📈" label="View Market Demand" to="/farming/demand" />
            <QuickAction icon="🌿" label="Browse Herb Database" to="/herbs" />
          </div>
        </div>
        <div className="card">
          <h3 className="section-title">My Recent Listings</h3>
          {isLoading ? <Spinner /> : listings?.length === 0 ? (
            <p className="text-gray-400 text-sm">No listings yet. <Link to="/farming/create" className="text-forest-600 underline">Create one</Link></p>
          ) : (
            <ul className="space-y-3">
              {listings?.slice(0, 4).map((l) => (
                <li key={l.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="font-medium text-gray-700">{l.herb?.name_english ?? "Herb"}</span>
                  <span className="text-gray-500">{l.quantity_kg} kg · ₦{l.price_per_kg}/kg</span>
                  <StatusBadge status={l.is_available ? "active" : "withdrawn"} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function ResearcherDashboard() {
  const { data: trials, isLoading } = useTrialList();
  const { data: herbs } = useHerbList({ limit: 5 });
  const verified = trials?.filter(t => t.is_verified).length ?? 0;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon="🔬" label="My Trials" value={isLoading ? "…" : (trials?.length ?? 0)} to="/research" />
        <StatCard icon="✅" label="Verified Trials" value={verified} to="/research" />
        <StatCard icon="🌿" label="Herb Database" value={herbs?.length ?? "…"} to="/herbs" />
        <StatCard icon="📊" label="Evidence Hub" value="Explore" to="/research/evidence" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction icon="📝" label="Submit Clinical Trial" to="/research/submit" />
            <QuickAction icon="📊" label="View Evidence Scores" to="/research/evidence" />
            <QuickAction icon="🔬" label="AI Herb Analysis" to="/herbs/scan" />
            <QuickAction icon="💊" label="Generate Formulation" to="/formulations/create" />
          </div>
        </div>
        <div className="card">
          <h3 className="section-title">Recent Trials</h3>
          {isLoading ? <Spinner /> : trials?.length === 0 ? (
            <p className="text-gray-400 text-sm">No trials yet. <Link to="/research/submit" className="text-forest-600 underline">Submit one</Link></p>
          ) : (
            <ul className="space-y-3">
              {trials?.slice(0, 4).map((t) => (
                <li key={t.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="font-medium text-gray-700 truncate flex-1">{t.study_title}</span>
                  <StatusBadge status={t.status} />
                  {t.is_verified && <span className="badge-green">✓</span>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function PharmaDashboard() {
  const { data: formulations, isLoading: fLoading } = useFormulationList();
  const { data: docs, isLoading: dLoading } = useComplianceDocuments();
  const { data: herbs } = useHerbList({ limit: 5 });
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon="💊" label="Formulations"   value={fLoading ? "…" : (formulations?.length ?? 0)} to="/formulations" />
        <StatCard icon="📋" label="Compliance Docs" value={dLoading ? "…" : (docs?.length ?? 0)}          to="/compliance" />
        <StatCard icon="🌿" label="Herbs Available" value={herbs?.length ?? "…"}                          to="/herbs" />
        <StatCard icon="🤖" label="AI Assistant"    value="Chat"                                          to="/compliance/chat" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction icon="🔬" label="Generate AI Formulation"    to="/formulations/create" />
            <QuickAction icon="🌾" label="Browse Herb Marketplace"    to="/farming" />
            <QuickAction icon="📋" label="New Compliance Document"    to="/compliance/create" />
            <QuickAction icon="🤖" label="NAFDAC AI Assistant"        to="/compliance/chat" />
          </div>
        </div>
        <div className="card">
          <h3 className="section-title">Compliance Documents</h3>
          {dLoading ? <Spinner /> : docs?.length === 0 ? (
            <p className="text-gray-400 text-sm">No documents yet. <Link to="/compliance/create" className="text-forest-600 underline">Create one</Link></p>
          ) : (
            <ul className="space-y-3">
              {docs?.slice(0, 4).map((d) => (
                <li key={d.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="font-medium text-gray-700 truncate flex-1">{d.product_name ?? d.document_type}</span>
                  <StatusBadge status={d.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function AdminDashboard() {
  const { data: herbs }        = useHerbList();
  const { data: trials }       = useTrialList();
  const { data: formulations } = useFormulationList();
  const unverified = trials?.filter(t => !t.is_verified && t.status === "completed").length ?? 0;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon="🌿" label="Total Herbs"   value={herbs?.length ?? "…"}          to="/herbs" />
        <StatCard icon="🔬" label="All Trials"    value={trials?.length ?? "…"}         to="/research" />
        <StatCard icon="💊" label="Formulations"  value={formulations?.length ?? "…"}   to="/formulations" />
        <StatCard icon="⚠️" label="Needs Verify"  value={unverified}                    to="/research" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="section-title">Admin Actions</h3>
          <div className="space-y-3">
            <QuickAction icon="🌿" label="Manage Herbs"         to="/herbs" />
            <QuickAction icon="✅" label="Verify Trials"        to="/research" />
            <QuickAction icon="💊" label="All Formulations"     to="/formulations" />
            <QuickAction icon="📋" label="Compliance Documents" to="/compliance" />
          </div>
        </div>
        <div className="card">
          <h3 className="section-title">Pending Verification</h3>
          {trials?.filter(t => !t.is_verified).length === 0 ? (
            <p className="text-gray-400 text-sm">All trials are verified ✅</p>
          ) : (
            <ul className="space-y-3">
              {trials?.filter(t => !t.is_verified).slice(0, 5).map((t) => (
                <li key={t.id} className="flex items-center justify-between text-sm gap-2">
                  <span className="font-medium text-gray-700 truncate flex-1">{t.study_title}</span>
                  <StatusBadge status={t.status} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  if (!user) return null;

  const greeting = (() => {
    const h = new Date().getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  })();

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <p className="text-forest-200 text-sm">{greeting},</p>
            <h1 className="text-2xl font-bold mt-0.5">{user.full_name} 👋</h1>
            <p className="text-forest-200 text-sm mt-1">
              {user.role === "farmer"         && "Manage your herb listings and track market demand."}
              {user.role === "researcher"     && "Submit trials, analyse evidence, and generate formulations."}
              {user.role === "pharma_company" && "Discover herbs, generate formulations, and file NAFDAC docs."}
              {user.role === "admin"          && "Oversee the full NigerFlora BioSciences ecosystem."}
            </p>
          </div>
          <div className="bg-forest-700/50 px-4 py-2 rounded-lg text-sm text-gold-300 font-medium">
            🇳🇬 {user.role === "farmer" ? "Farmer" : user.role === "researcher" ? "Researcher" : user.role === "pharma_company" ? "Pharma Company" : "Admin"}
          </div>
        </div>
      </div>

      {user.role === "farmer"         && <FarmerDashboard />}
      {user.role === "researcher"     && <ResearcherDashboard />}
      {user.role === "pharma_company" && <PharmaDashboard />}
      {user.role === "admin"          && <AdminDashboard />}
    </div>
  );
}
