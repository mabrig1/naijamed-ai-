import { Link } from "react-router-dom";
import { useFormulationList, usePublishFormulation } from "../../hooks/useFormulations";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { DrugFormulation } from "../../types";

function FormulationCard({ f, onPublish }: { f: DrugFormulation; onPublish: (id: number) => void }) {
  const typeIcon: Record<string, string> = { tablet: "💊", syrup: "🧴", extract: "🌿", capsule: "💉", cream: "🫙" };
  return (
    <Link to={`/formulations/${f.id}`} className="card-hover group block">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <span className="text-3xl">{typeIcon[f.formulation_type] ?? "💊"}</span>
          <div>
            <div className="font-bold text-forest-700 capitalize">{f.formulation_type}</div>
            {f.target_disease && <div className="text-xs text-gray-500">For: {f.target_disease}</div>}
          </div>
        </div>
        {f.is_published
          ? <span className="badge-green">Published</span>
          : <span className="badge-gray">Draft</span>
        }
      </div>
      {f.dosage_suggestion && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">📋 {f.dosage_suggestion}</p>
      )}
      {f.estimated_cost_savings_usd && (
        <p className="text-sm text-forest-600 font-medium">💰 Est. savings: ${f.estimated_cost_savings_usd}/1k units</p>
      )}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-100">
        <span className="text-xs text-gray-400">{new Date(f.created_at).toLocaleDateString()}</span>
        {!f.is_published && (
          <button
            onClick={(e) => { e.preventDefault(); onPublish(f.id); }}
            className="text-xs btn-outline py-1 px-3 border-forest-400 text-forest-600"
          >
            Publish
          </button>
        )}
      </div>
    </Link>
  );
}

export default function FormulationList() {
  const { data: formulations, isLoading, isError } = useFormulationList();
  const publishMut = usePublishFormulation();
  const { data: herbs } = useHerbList({ limit: 100 });

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">💊 Drug Formulations</h1>
          <p className="text-forest-200 text-sm mt-1">AI-generated pharmaceutical formulations for Nigerian herbs</p>
        </div>
        <Link to="/formulations/create" className="btn-secondary text-sm">➕ Generate Formulation</Link>
      </div>

      {/* Stats bar */}
      {formulations && (
        <div className="grid grid-cols-3 gap-4">
          <div className="card text-center">
            <div className="text-2xl font-bold text-forest-700">{formulations.length}</div>
            <div className="text-xs text-gray-500">Total</div>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold text-forest-700">{formulations.filter(f => f.is_published).length}</div>
            <div className="text-xs text-gray-500">Published</div>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold text-forest-700">{herbs?.length ?? "…"}</div>
            <div className="text-xs text-gray-500">Herbs Available</div>
          </div>
        </div>
      )}

      {isLoading && <div className="flex justify-center py-12"><Spinner /></div>}
      {isError   && <PageError message="Failed to load formulations." />}
      {!isLoading && formulations?.length === 0 && (
        <Empty icon="💊" title="No formulations yet" subtitle="Generate your first AI formulation to get started." />
      )}
      {!isLoading && formulations && formulations.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {formulations.map((f) => (
            <FormulationCard key={f.id} f={f} onPublish={(id) => publishMut.mutate(id)} />
          ))}
        </div>
      )}
    </div>
  );
}
