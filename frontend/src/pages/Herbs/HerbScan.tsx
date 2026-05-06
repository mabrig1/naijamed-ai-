import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useScanHerb } from "../../hooks/useHerbs";
import { Spinner } from "../../components/Layout";
import type { ScanResponse } from "../../types";

function ScanSection({ title, items, icon }: { title: string; items: string[]; icon: string }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="card">
      <h3 className="font-semibold text-forest-700 flex items-center gap-2 mb-3">
        <span>{icon}</span> {title}
      </h3>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600 flex gap-2">
            <span className="text-forest-400 shrink-0 mt-0.5">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function HerbScan() {
  const location = useLocation();
  const [herbName, setHerbName]     = useState((location.state as { herbName?: string })?.herbName ?? "");
  const [description, setDescription] = useState("");
  const [result, setResult]         = useState<ScanResponse | null>(null);
  const scanMut = useScanHerb();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await scanMut.mutateAsync({ herb_name: herbName, user_description: description });
    setResult(res);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">🔍 AI Herb Scanner</h1>
        <p className="text-forest-200 text-sm mt-1">
          Enter any Nigerian herb name and get a full AI analysis powered by Google Gemini.
        </p>
      </div>

      {/* Form */}
      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="label">Herb Name <span className="text-red-500">*</span></label>
            <input className="input" placeholder="e.g. Bitter Leaf, Neem, Moringa, Scent Leaf"
              value={herbName} onChange={(e) => setHerbName(e.target.value)} required />
          </div>
          <div>
            <label className="label">Additional Context <span className="text-gray-400">(optional)</span></label>
            <textarea className="input min-h-24 resize-none" rows={3}
              placeholder="Describe what you know, your use case, or any specific questions…"
              value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={scanMut.isPending}>
            {scanMut.isPending ? <><Spinner /> Analysing with AI…</> : "🔬 Scan Herb →"}
          </button>
        </form>

        {scanMut.isError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            ⚠️ Scan failed. Check that your API key is configured and try again.
          </div>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4">
          <div className="card bg-forest-600 text-white">
            <div className="flex items-center gap-3">
              <span className="text-4xl">🌿</span>
              <div>
                <h2 className="text-2xl font-bold">{result.herb_name}</h2>
                {result.scientific_name && <p className="text-forest-200 italic text-sm">{result.scientific_name}</p>}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <ScanSection title="Medicinal Properties"   icon="💚" items={result.medicinal_properties} />
            <ScanSection title="Diseases Treated"       icon="🩺" items={result.diseases_treated} />
            <ScanSection title="Drug Production Pathways" icon="🏭" items={result.drug_production_pathways} />
            <ScanSection title="Research Gaps"          icon="🔭" items={result.research_gaps} />
          </div>

          {/* Active compounds */}
          {result.active_compounds?.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-forest-700 flex items-center gap-2 mb-3">
                <span>⚗️</span> Active Compounds
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {result.active_compounds.map((c, i) => (
                  <div key={i} className="bg-forest-50 rounded-lg p-3 border border-forest-100">
                    <div className="font-semibold text-sm text-forest-700">{c.name}</div>
                    {c.formula && <div className="text-xs font-mono text-gray-500 mt-0.5">{c.formula}</div>}
                    {c.role    && <div className="text-xs text-gray-600 mt-1">{c.role}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Safety warnings */}
          {result.safety_warnings?.length > 0 && (
            <div className="card border-amber-200 bg-amber-50">
              <h3 className="font-semibold text-amber-700 flex items-center gap-2 mb-3">
                <span>⚠️</span> Safety Warnings
              </h3>
              <ul className="space-y-1.5">
                {result.safety_warnings.map((w, i) => (
                  <li key={i} className="text-sm text-amber-800 flex gap-2">
                    <span className="shrink-0">!</span> {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
