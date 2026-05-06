import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useHerbDetail, useDrugSuggestion } from "../../hooks/useHerbs";
import { useHerbEvidence } from "../../hooks/useResearch";
import { Spinner, PageError, ProgressBar } from "../../components/Layout";
import type { DrugSuggestionResponse } from "../../types";

export default function HerbDetail() {
  const { id } = useParams<{ id: string }>();
  const herbId = Number(id);
  const { data: herb, isLoading, isError } = useHerbDetail(herbId);
  const { data: evidence, isLoading: evLoading } = useHerbEvidence(herbId);
  const suggestMut = useDrugSuggestion(herbId);

  const [disease, setDisease] = useState("");
  const [suggestion, setSuggestion] = useState<DrugSuggestionResponse | null>(null);

  async function handleSuggest(e: React.FormEvent) {
    e.preventDefault();
    const res = await suggestMut.mutateAsync({ target_disease: disease });
    setSuggestion(res);
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;
  if (isError || !herb) return <PageError message="Herb not found." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="w-16 h-16 bg-forest-500 rounded-2xl flex items-center justify-center text-4xl shrink-0">🌿</div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold">{herb.name_english}</h1>
            {herb.scientific_name && <p className="italic text-forest-200 text-sm">{herb.scientific_name}</p>}
            <div className="flex flex-wrap gap-2 mt-2">
              {herb.name_yoruba && <span className="bg-forest-700/50 text-forest-100 text-xs px-2.5 py-1 rounded-full">Yoruba: <b>{herb.name_yoruba}</b></span>}
              {herb.name_igbo   && <span className="bg-forest-700/50 text-forest-100 text-xs px-2.5 py-1 rounded-full">Igbo: <b>{herb.name_igbo}</b></span>}
              {herb.name_hausa  && <span className="bg-forest-700/50 text-forest-100 text-xs px-2.5 py-1 rounded-full">Hausa: <b>{herb.name_hausa}</b></span>}
            </div>
          </div>
          <div className="flex gap-3 flex-wrap">
            <Link to="/herbs/scan" state={{ herbName: herb.name_english }} className="btn-secondary text-sm">🔍 AI Scan</Link>
            <Link to="/formulations/create" state={{ herbId: herb.id }} className="btn-outline border-white text-white hover:bg-white/10 text-sm">💊 Formulate</Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          {herb.description && (
            <div className="card">
              <h2 className="section-title">About this Herb</h2>
              <p className="text-gray-600 leading-relaxed">{herb.description}</p>
              {herb.region_found && (
                <div className="mt-4 flex items-center gap-2 text-sm text-earth-500 font-medium">
                  <span>📍</span> Found in: {herb.region_found}
                </div>
              )}
            </div>
          )}

          {/* Compounds */}
          {herb.compounds?.length > 0 && (
            <div className="card">
              <h2 className="section-title">Active Compounds ({herb.compounds.length})</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-forest-100">
                      <th className="text-left py-2 pr-4 font-semibold text-forest-700">Compound</th>
                      <th className="text-left py-2 pr-4 font-semibold text-forest-700">Formula</th>
                      <th className="text-left py-2 font-semibold text-forest-700">Medicinal Use</th>
                    </tr>
                  </thead>
                  <tbody>
                    {herb.compounds.map((c) => (
                      <tr key={c.id} className="border-b border-gray-50 hover:bg-forest-50 transition-colors">
                        <td className="py-2 pr-4 font-medium text-forest-700">{c.compound_name}</td>
                        <td className="py-2 pr-4 text-gray-500 font-mono text-xs">{c.chemical_formula ?? "—"}</td>
                        <td className="py-2 text-gray-600 text-xs">{c.medicinal_use ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Drug suggestion form */}
          <div className="card">
            <h2 className="section-title">AI Drug Possibility</h2>
            <p className="text-sm text-gray-500 mb-4">Enter a target disease to get an AI assessment of this herb's pharmaceutical potential.</p>
            <form onSubmit={handleSuggest} className="flex gap-3 flex-wrap">
              <input className="input flex-1 min-w-48" placeholder="e.g. Type 2 Diabetes, Malaria, Hypertension"
                value={disease} onChange={(e) => setDisease(e.target.value)} required />
              <button type="submit" className="btn-primary shrink-0" disabled={suggestMut.isPending}>
                {suggestMut.isPending ? <Spinner /> : "Assess →"}
              </button>
            </form>

            {suggestion && (
              <div className="mt-6 space-y-4">
                <div>
                  <ProgressBar value={suggestion.feasibility_score} label="Feasibility Score" />
                </div>
                <p className="text-sm text-gray-700 leading-relaxed"><b className="text-forest-700">Mechanism:</b> {suggestion.mechanism_of_action}</p>
                {suggestion.relevant_compounds.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-forest-700 mb-1.5">Relevant Compounds</p>
                    <div className="flex flex-wrap gap-1.5">{suggestion.relevant_compounds.map(c => <span key={c} className="badge-green">{c}</span>)}</div>
                  </div>
                )}
                <p className="text-sm text-gray-700"><b className="text-forest-700">Timeline:</b> {suggestion.estimated_timeline_years}</p>
                <p className="text-sm text-gray-700"><b className="text-forest-700">Regulatory:</b> {suggestion.regulatory_considerations}</p>
                {suggestion.risks.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-red-600 mb-1.5">Risks</p>
                    <ul className="list-disc pl-4 space-y-1">{suggestion.risks.map((r,i) => <li key={i} className="text-sm text-gray-600">{r}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right column — Evidence score */}
        <div className="space-y-6">
          <div className="card">
            <h2 className="section-title">Evidence Score</h2>
            {evLoading ? <Spinner /> : evidence ? (
              <div className="space-y-4">
                <div className="text-center">
                  <div className="text-5xl font-bold text-forest-700">{evidence.evidence_score}</div>
                  <div className="text-xs text-gray-400 mt-1">out of 100</div>
                  <div className={`mt-2 inline-block px-3 py-1 rounded-full text-sm font-semibold ${
                    evidence.verdict === "Promising" ? "bg-forest-100 text-forest-700" :
                    evidence.verdict === "Not recommended" ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{evidence.verdict}</div>
                </div>
                <ProgressBar value={evidence.evidence_score} />
                <div className="text-xs text-gray-500 text-center">
                  {evidence.trial_count} trial(s) · {evidence.verified_trial_count} verified
                </div>
                {evidence.key_findings.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-forest-700 mb-2">Key Findings</p>
                    <ul className="space-y-1.5">
                      {evidence.key_findings.map((f,i) => <li key={i} className="text-xs text-gray-600 flex gap-1.5"><span className="text-forest-400 shrink-0">•</span>{f}</li>)}
                    </ul>
                  </div>
                )}
                {evidence.safety_signals.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold text-amber-600 mb-2">Safety Signals</p>
                    <ul className="space-y-1.5">
                      {evidence.safety_signals.map((s,i) => <li key={i} className="text-xs text-gray-600 flex gap-1.5"><span className="text-amber-400 shrink-0">⚠</span>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No trials submitted yet for this herb.</p>
            )}
          </div>

          <div className="card bg-forest-50 border-forest-200">
            <h3 className="font-semibold text-forest-700 mb-3">Quick Links</h3>
            <div className="space-y-2 text-sm">
              <Link to="/research/submit" state={{ herbId: herb.id }} className="block text-forest-600 hover:underline">📝 Submit a clinical trial</Link>
              <Link to="/formulations/create" state={{ herbId: herb.id }} className="block text-forest-600 hover:underline">💊 Generate formulation</Link>
              <Link to="/herbs/scan" state={{ herbName: herb.name_english }} className="block text-forest-600 hover:underline">🔍 AI herb scan</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
