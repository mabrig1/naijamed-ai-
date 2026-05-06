import { useState } from "react";
import { Link } from "react-router-dom";
import { useHerbList } from "../../hooks/useHerbs";
import { useHerbEvidence } from "../../hooks/useResearch";
import { Spinner, PageError, ProgressBar } from "../../components/Layout";

export default function HerbEvidence() {
  const [selectedHerbId, setSelectedHerbId] = useState<number | null>(null);
  const { data: herbs, isLoading: herbsLoading } = useHerbList({ limit: 100 });
  const { data: evidence, isLoading: evLoading, isError } = useHerbEvidence(selectedHerbId ?? 0);

  const selectedHerb = herbs?.find((h) => h.id === selectedHerbId);

  const verdictStyle: Record<string, { bg: string; text: string }> = {
    "Promising":           { bg: "bg-forest-100", text: "text-forest-700" },
    "Needs more study":    { bg: "bg-yellow-100",  text: "text-yellow-700" },
    "Not recommended":     { bg: "bg-red-100",     text: "text-red-700" },
  };

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">🧬 Herb Evidence Database</h1>
        <p className="text-forest-200 text-sm mt-1">
          AI-generated evidence scores based on submitted clinical trials and outcomes.
        </p>
      </div>

      {/* Herb picker */}
      <div className="card">
        <label className="label">Select a Herb to View Evidence</label>
        {herbsLoading ? (
          <div className="flex justify-center py-4"><Spinner /></div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mt-2">
            {herbs?.map((herb) => (
              <button
                key={herb.id}
                type="button"
                onClick={() => setSelectedHerbId(herb.id)}
                className={`text-left p-3 rounded-xl border-2 transition-all ${
                  selectedHerbId === herb.id
                    ? "border-forest-600 bg-forest-50"
                    : "border-gray-200 hover:border-forest-300"
                }`}
              >
                <p className="font-semibold text-sm text-forest-700 line-clamp-1">{herb.name_english}</p>
                {herb.scientific_name && (
                  <p className="text-xs italic text-gray-400 line-clamp-1">{herb.scientific_name}</p>
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {selectedHerbId && (
        <>
          {evLoading && <div className="flex justify-center py-12"><Spinner /></div>}
          {isError && <PageError message="Failed to load evidence score. The AI may still be processing." />}

          {!evLoading && !evidence && !isError && (
            <div className="card text-center py-12">
              <p className="text-4xl mb-3">🔬</p>
              <p className="font-semibold text-gray-700">No evidence data yet for {selectedHerb?.name_english}</p>
              <p className="text-sm text-gray-500 mt-1">Submit a clinical trial to start building the evidence base.</p>
              <Link to="/research/submit" state={{ herbId: selectedHerbId }} className="btn-primary mt-4 inline-block text-sm">
                Submit a Trial
              </Link>
            </div>
          )}

          {evidence && (
            <div className="space-y-6">
              {/* Score card */}
              <div className="card">
                <div className="flex items-center gap-6 flex-wrap">
                  <div className="text-center">
                    <div className="text-6xl font-bold text-forest-700">{evidence.evidence_score}</div>
                    <div className="text-xs text-gray-400 mt-1">Evidence Score / 100</div>
                  </div>
                  <div className="flex-1 min-w-48 space-y-3">
                    <ProgressBar value={evidence.evidence_score} label="Overall Evidence" />
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className={`text-sm font-semibold px-3 py-1 rounded-full ${
                        verdictStyle[evidence.verdict]?.bg ?? "bg-gray-100"
                      } ${verdictStyle[evidence.verdict]?.text ?? "text-gray-700"}`}>
                        {evidence.verdict}
                      </span>
                      <span className="text-sm text-gray-500">
                        {evidence.trial_count} trial{evidence.trial_count !== 1 ? "s" : ""} · {evidence.verified_trial_count} verified
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Key findings */}
                {evidence.key_findings?.length > 0 && (
                  <div className="card">
                    <h2 className="section-title mb-3">Key Findings</h2>
                    <ul className="space-y-2">
                      {evidence.key_findings.map((finding, i) => (
                        <li key={i} className="text-sm text-gray-700 flex gap-2">
                          <span className="text-forest-400 shrink-0 mt-0.5">•</span>
                          <span>{finding}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Safety signals */}
                {evidence.safety_signals?.length > 0 && (
                  <div className="card border-amber-200 bg-amber-50">
                    <h2 className="font-semibold text-amber-700 mb-3">⚠️ Safety Signals</h2>
                    <ul className="space-y-2">
                      {evidence.safety_signals.map((signal, i) => (
                        <li key={i} className="text-sm text-amber-800 flex gap-2">
                          <span className="shrink-0">!</span>
                          <span>{signal}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="flex gap-3 flex-wrap">
                <Link to="/research/submit" state={{ herbId: selectedHerbId }} className="btn-primary text-sm">
                  📝 Submit a Trial
                </Link>
                <Link to={`/herbs/${selectedHerbId}`} className="btn-outline text-sm">
                  🌿 View Herb Profile
                </Link>
                <Link to="/formulations/create" state={{ herbId: selectedHerbId }} className="btn-outline text-sm">
                  💊 Generate Formulation
                </Link>
              </div>
            </div>
          )}
        </>
      )}

      {!selectedHerbId && (
        <div className="card text-center py-12 text-gray-400">
          <p className="text-4xl mb-3">🧬</p>
          <p className="text-sm">Select a herb above to view its evidence score and research findings.</p>
        </div>
      )}
    </div>
  );
}
