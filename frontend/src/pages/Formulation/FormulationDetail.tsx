import { useState } from "react";
import { useParams } from "react-router-dom";
import { useFormulationDetail, usePublishFormulation, useCompareFormulations } from "../../hooks/useFormulations";
import { useHerbDetail } from "../../hooks/useHerbs";
import { Spinner, PageError } from "../../components/Layout";

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="card">
      <h3 className="font-semibold text-forest-700 flex items-center gap-2 mb-4">
        <span>{icon}</span> {title}
      </h3>
      {children}
    </div>
  );
}

export default function FormulationDetail() {
  const { id } = useParams<{ id: string }>();
  const formId = Number(id);
  const { data: f, isLoading, isError } = useFormulationDetail(formId);
  const { data: herb } = useHerbDetail(f?.herb_id ?? 0);
  const publishMut = usePublishFormulation();
  const compareMut = useCompareFormulations();
  const [compareId, setCompareId] = useState("");

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;
  if (isError || !f) return <PageError message="Formulation not found." />;

  const typeIcon: Record<string, string> = { tablet: "💊", syrup: "🧴", extract: "🌿", capsule: "💉", cream: "🫙" };

  function handlePrint() { window.print(); }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <span className="text-4xl">{typeIcon[f.formulation_type] ?? "💊"}</span>
            <div>
              <h1 className="text-2xl font-bold capitalize">{f.formulation_type} Formulation</h1>
              {herb && <p className="text-forest-200 text-sm">{herb.name_english}{herb.scientific_name ? ` · ${herb.scientific_name}` : ""}</p>}
              {f.target_disease && <p className="text-forest-300 text-xs mt-0.5">For: {f.target_disease}</p>}
            </div>
          </div>
          <div className="flex gap-3 flex-wrap">
            {!f.is_published && (
              <button onClick={() => publishMut.mutate(formId)} className="btn-secondary text-sm" disabled={publishMut.isPending}>
                {publishMut.isPending ? <Spinner /> : "📢 Publish"}
              </button>
            )}
            <button onClick={handlePrint} className="btn-outline border-white text-white hover:bg-white/10 text-sm">
              🖨️ Export PDF
            </button>
          </div>
        </div>
      </div>

      {f.is_published && (
        <div className="bg-forest-100 border border-forest-300 text-forest-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          ✅ This formulation is published and visible to pharma buyers.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Dosage */}
          {f.dosage_suggestion && (
            <Section title="Dosage & Administration" icon="📋">
              <p className="text-gray-700">{f.dosage_suggestion}</p>
            </Section>
          )}

          {/* Manufacturing */}
          {f.manufacturing_process_summary && (
            <Section title="Manufacturing Process" icon="🏭">
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{f.manufacturing_process_summary}</p>
            </Section>
          )}

          {/* Excipients */}
          {f.excipients_needed && f.excipients_needed.length > 0 && (
            <Section title="Excipients & Ingredients" icon="⚗️">
              <ul className="space-y-2">
                {f.excipients_needed.map((e, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-700">
                    <span className="text-forest-400 shrink-0 mt-0.5">•</span> {e}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {/* Next steps */}
          {f.next_steps && f.next_steps.length > 0 && (
            <Section title="Next Development Steps" icon="🗺️">
              <ol className="space-y-2">
                {f.next_steps.map((s, i) => (
                  <li key={i} className="flex gap-3 text-sm text-gray-700">
                    <span className="w-6 h-6 bg-forest-100 text-forest-700 rounded-full flex items-center justify-center font-bold text-xs shrink-0">{i + 1}</span>
                    {s}
                  </li>
                ))}
              </ol>
            </Section>
          )}

          {/* AI notes */}
          {f.ai_notes && (
            <Section title="AI Scientific Notes" icon="🤖">
              <p className="text-gray-700 leading-relaxed">{f.ai_notes}</p>
            </Section>
          )}

          {/* Disclaimer */}
          {f.disclaimer && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
              <span className="font-semibold">⚠️ Disclaimer: </span>{f.disclaimer}
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="font-semibold text-forest-700 mb-4">Quick Stats</h3>
            <div className="space-y-3 text-sm">
              {f.stability_prediction && (
                <div><span className="text-gray-500">Stability:</span> <span className="font-medium">{f.stability_prediction}</span></div>
              )}
              {f.estimated_cost_savings_usd != null && (
                <div><span className="text-gray-500">Est. savings:</span> <span className="font-medium text-forest-600">${f.estimated_cost_savings_usd}/1k units</span></div>
              )}
              {f.compound_used && (
                <div><span className="text-gray-500">Key compound:</span> <span className="font-medium">{f.compound_used}</span></div>
              )}
            </div>
          </div>

          {f.side_effects_prediction && (
            <div className="card border-amber-200 bg-amber-50">
              <h3 className="font-semibold text-amber-700 mb-2">⚠️ Predicted Side Effects</h3>
              <p className="text-sm text-amber-800">{f.side_effects_prediction}</p>
            </div>
          )}

          {/* Compare */}
          <div className="card">
            <h3 className="font-semibold text-forest-700 mb-3">Compare Formulations</h3>
            <div className="flex gap-2">
              <input className="input text-sm flex-1" placeholder="Other formulation ID"
                value={compareId} onChange={(e) => setCompareId(e.target.value)} />
              <button className="btn-primary text-sm shrink-0 px-3"
                disabled={compareMut.isPending || !compareId}
                onClick={() => compareMut.mutate({ formulation_id_1: formId, formulation_id_2: Number(compareId) })}>
                {compareMut.isPending ? <Spinner /> : "Go"}
              </button>
            </div>
            {compareMut.data && (
              <div className="mt-4 space-y-3 text-sm">
                <div className="bg-forest-50 rounded-lg p-3">
                  <p className="font-semibold text-forest-700 mb-1">Recommended: #{compareMut.data.recommended_id}</p>
                  <p className="text-gray-600">{compareMut.data.reasoning}</p>
                </div>
                {compareMut.data.trade_offs.length > 0 && (
                  <div>
                    <p className="font-medium text-gray-600 mb-1">Trade-offs:</p>
                    <ul className="space-y-1">{compareMut.data.trade_offs.map((t,i) => <li key={i} className="text-xs text-gray-500">• {t}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
