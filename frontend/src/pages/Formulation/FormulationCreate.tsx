import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useHerbList } from "../../hooks/useHerbs";
import { useGenerateFormulation } from "../../hooks/useFormulations";
import { Spinner, PageError } from "../../components/Layout";
import type { FormulationType } from "../../types";

const TYPES: { value: FormulationType; label: string; icon: string }[] = [
  { value: "tablet",  label: "Tablet",  icon: "💊" },
  { value: "capsule", label: "Capsule", icon: "💉" },
  { value: "syrup",   label: "Syrup",   icon: "🧴" },
  { value: "extract", label: "Extract", icon: "🌿" },
  { value: "cream",   label: "Cream",   icon: "🫙" },
];

export default function FormulationCreate() {
  const navigate = useNavigate();
  const location = useLocation();

  const [herbId,     setHerbId]     = useState<string>((location.state as { herbId?: number })?.herbId?.toString() ?? "");
  const [disease,    setDisease]    = useState("");
  const [compound,   setCompound]   = useState("");
  const [formType,   setFormType]   = useState<FormulationType>("tablet");

  const { data: herbs } = useHerbList({ limit: 100 });
  const generateMut = useGenerateFormulation();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const res = await generateMut.mutateAsync({
      herb_id: Number(herbId),
      target_disease: disease,
      compound_used: compound || undefined,
      formulation_type: formType,
    });
    navigate(`/formulations/${res.id}`);
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">🔬 Generate AI Formulation</h1>
        <p className="text-forest-200 text-sm mt-1">
          Claude will design a complete pharmaceutical formulation based on the herb you select.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Herb select */}
          <div>
            <label className="label">Select Herb <span className="text-red-500">*</span></label>
            <select className="select" value={herbId} onChange={(e) => setHerbId(e.target.value)} required>
              <option value="">— Choose a herb —</option>
              {herbs?.map((h) => (
                <option key={h.id} value={h.id}>{h.name_english}{h.scientific_name ? ` (${h.scientific_name})` : ""}</option>
              ))}
            </select>
          </div>

          {/* Formulation type */}
          <div>
            <label className="label">Formulation Type <span className="text-red-500">*</span></label>
            <div className="grid grid-cols-5 gap-2">
              {TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setFormType(t.value)}
                  className={`flex flex-col items-center gap-1 p-3 rounded-xl border-2 transition-all ${
                    formType === t.value
                      ? "border-forest-600 bg-forest-50 text-forest-700"
                      : "border-gray-200 hover:border-forest-300 text-gray-500"
                  }`}
                >
                  <span className="text-2xl">{t.icon}</span>
                  <span className="text-xs font-medium">{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Target disease */}
          <div>
            <label className="label">Target Disease / Condition <span className="text-red-500">*</span></label>
            <input className="input" placeholder="e.g. Type 2 Diabetes, Malaria, Hypertension, Arthritis"
              value={disease} onChange={(e) => setDisease(e.target.value)} required />
          </div>

          {/* Key compound */}
          <div>
            <label className="label">Key Active Compound <span className="text-gray-400">(optional)</span></label>
            <input className="input" placeholder="e.g. Quercetin, Azadirachtin, Curcumin"
              value={compound} onChange={(e) => setCompound(e.target.value)} />
            <p className="text-xs text-gray-400 mt-1.5">Leave blank to let Claude identify the primary compound.</p>
          </div>

          {generateMut.isError && (
            <PageError message="AI generation failed. Check your Anthropic API key and try again." />
          )}

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-800">
            ⏱️ <b>Note:</b> AI generation takes 15–30 seconds. Please wait after clicking Generate.
          </div>

          <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2 py-3"
            disabled={generateMut.isPending || !herbId || !disease}>
            {generateMut.isPending
              ? <><Spinner /> Claude is designing your formulation…</>
              : "🤖 Generate AI Formulation →"}
          </button>
        </form>
      </div>
    </div>
  );
}
