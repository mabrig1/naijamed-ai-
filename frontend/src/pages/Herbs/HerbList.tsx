import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { Herb } from "../../types";

function HerbCard({ herb }: { herb: Herb }) {
  const navigate = useNavigate();
  return (
    <div className="card-hover group" onClick={() => navigate(`/herbs/${herb.id}`)}>
      <div className="flex items-start justify-between mb-3">
        <div className="w-12 h-12 bg-forest-100 rounded-xl flex items-center justify-center text-2xl shrink-0">🌿</div>
        <Link
          to="/herbs/scan"
          state={{ herbName: herb.name_english }}
          onClick={(e) => e.stopPropagation()}
          className="text-xs btn-outline py-1 px-3 border-forest-400 text-forest-600 hover:bg-forest-50"
        >
          AI Scan
        </Link>
      </div>
      <h3 className="font-bold text-forest-700 text-lg leading-tight">{herb.name_english}</h3>
      {herb.scientific_name && (
        <p className="text-xs italic text-gray-400 mb-2">{herb.scientific_name}</p>
      )}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {herb.name_yoruba && <span className="badge-green text-xs">Yoruba: {herb.name_yoruba}</span>}
        {herb.name_igbo   && <span className="badge-gold  text-xs">Igbo: {herb.name_igbo}</span>}
        {herb.name_hausa  && <span className="badge-gray  text-xs">Hausa: {herb.name_hausa}</span>}
      </div>
      {herb.description && (
        <p className="text-sm text-gray-500 line-clamp-2 leading-relaxed">{herb.description}</p>
      )}
      {herb.region_found && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-earth-500">
          <span>📍</span> {herb.region_found}
        </div>
      )}
    </div>
  );
}

export default function HerbList() {
  const [search, setSearch]   = useState("");
  const [region, setRegion]   = useState("");
  const [compound, setCompound] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Simple debounce via timeout (no extra library needed)
  let debTimer: ReturnType<typeof setTimeout>;
  function onSearchChange(v: string) {
    setSearch(v);
    clearTimeout(debTimer);
    debTimer = setTimeout(() => setDebouncedSearch(v), 400);
  }

  const { data: herbs, isLoading, isError, error } = useHerbList({
    search: debouncedSearch || undefined,
    region: region || undefined,
    compound: compound || undefined,
    limit: 100,
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold">🌿 Herb Database</h1>
            <p className="text-forest-200 text-sm mt-1">
              {herbs ? `${herbs.length} Nigerian medicinal herbs` : "Browse the full collection"}
            </p>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Link to="/herbs/scan" className="btn-secondary text-sm">🔍 AI Scan</Link>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Search herbs</label>
            <input className="input" placeholder="Name in English, Yoruba, Igbo, Hausa…"
              value={search} onChange={(e) => onSearchChange(e.target.value)} />
          </div>
          <div>
            <label className="label">Filter by region</label>
            <input className="input" placeholder="e.g. South West, North Nigeria…"
              value={region} onChange={(e) => setRegion(e.target.value)} />
          </div>
          <div>
            <label className="label">Filter by compound</label>
            <input className="input" placeholder="e.g. Quercetin, Azadirachtin…"
              value={compound} onChange={(e) => setCompound(e.target.value)} />
          </div>
        </div>
        {(search || region || compound) && (
          <button className="btn-ghost text-sm mt-3" onClick={() => { setSearch(""); setRegion(""); setCompound(""); setDebouncedSearch(""); }}>
            ✕ Clear filters
          </button>
        )}
      </div>

      {/* Results */}
      {isLoading && (
        <div className="flex justify-center py-12"><Spinner /></div>
      )}
      {isError && (
        <PageError message={(error as { message?: string })?.message ?? "Failed to load herbs."} />
      )}
      {!isLoading && herbs?.length === 0 && (
        <Empty icon="🌿" title="No herbs found" subtitle="Try adjusting your search filters." />
      )}
      {!isLoading && herbs && herbs.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {herbs.map((herb) => <HerbCard key={herb.id} herb={herb} />)}
        </div>
      )}
    </div>
  );
}
