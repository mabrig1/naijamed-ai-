import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateComplianceDocument, useGenerateComplianceDocument, useNafdacChecklist } from "../../hooks/useCompliance";
import { useHerbList } from "../../hooks/useHerbs";
import { useFormulationList } from "../../hooks/useFormulations";
import { Spinner, PageError } from "../../components/Layout";

const DOC_TYPES = [
  { value: "product_dossier",      label: "Product Dossier",      icon: "📚" },
  { value: "manufacturing_license", label: "Manufacturing License", icon: "🏭" },
  { value: "labeling_document",    label: "Labeling Document",    icon: "🏷️" },
  { value: "safety_report",        label: "Safety Report",        icon: "🛡️" },
  { value: "clinical_summary",     label: "Clinical Summary",     icon: "🔬" },
];

const PRODUCT_TYPES = ["herbal", "supplement", "cosmetic", "pharmaceutical"];

export default function DocumentCreate() {
  const navigate = useNavigate();
  const { data: herbs } = useHerbList({ limit: 100 });
  const { data: formulations } = useFormulationList();

  const createMut   = useCreateComplianceDocument();
  const generateMut = useGenerateComplianceDocument();

  const [herbId, setHerbId]           = useState("");
  const [formulationId, setFormulationId] = useState("");
  const [docType, setDocType]         = useState("product_dossier");
  const [productType, setProductType] = useState("herbal");
  const [docId, setDocId]             = useState<number | null>(null);

  const { data: checklist } = useNafdacChecklist(productType);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const res = await createMut.mutateAsync({
      herb_id: herbId ? Number(herbId) : undefined,
      formulation_id: formulationId ? Number(formulationId) : undefined,
      document_type: docType,
      product_type: productType,
    });
    setDocId(res.id);
  }

  async function handleAIGenerate() {
    if (!docId) return;
    await generateMut.mutateAsync(docId);
    navigate(`/compliance/${docId}`);
  }

  const publishedFormulations = formulations?.filter((f) => f.is_published) ?? [];

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">📋 New Compliance Document</h1>
        <p className="text-forest-200 text-sm mt-1">
          Claude AI will auto-fill your NAFDAC document based on the herb and formulation you select.
        </p>
      </div>

      {!docId ? (
        <div className="card">
          <form onSubmit={handleCreate} className="space-y-6">
            {/* Document type */}
            <div>
              <label className="label">Document Type <span className="text-red-500">*</span></label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
                {DOC_TYPES.map((t) => (
                  <button
                    key={t.value}
                    type="button"
                    onClick={() => setDocType(t.value)}
                    className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                      docType === t.value
                        ? "border-forest-600 bg-forest-50 text-forest-700"
                        : "border-gray-200 hover:border-forest-300 text-gray-600"
                    }`}
                  >
                    <span className="text-xl shrink-0">{t.icon}</span>
                    <span className="text-sm font-medium">{t.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Product type */}
            <div>
              <label className="label">Product Category <span className="text-red-500">*</span></label>
              <div className="flex flex-wrap gap-2">
                {PRODUCT_TYPES.map((pt) => (
                  <button
                    key={pt}
                    type="button"
                    onClick={() => setProductType(pt)}
                    className={`px-4 py-2 rounded-full border-2 text-sm font-medium transition-all capitalize ${
                      productType === pt
                        ? "border-forest-600 bg-forest-600 text-white"
                        : "border-gray-200 text-gray-600 hover:border-forest-300"
                    }`}
                  >
                    {pt}
                  </button>
                ))}
              </div>
            </div>

            {/* Herb */}
            <div>
              <label className="label">Primary Herb <span className="text-gray-400">(optional)</span></label>
              <select className="select" value={herbId} onChange={(e) => setHerbId(e.target.value)}>
                <option value="">— Not specified —</option>
                {herbs?.map((h) => (
                  <option key={h.id} value={h.id}>{h.name_english}{h.scientific_name ? ` (${h.scientific_name})` : ""}</option>
                ))}
              </select>
            </div>

            {/* Formulation */}
            <div>
              <label className="label">Linked Formulation <span className="text-gray-400">(optional)</span></label>
              <select className="select" value={formulationId} onChange={(e) => setFormulationId(e.target.value)}>
                <option value="">— None —</option>
                {publishedFormulations.map((f) => (
                  <option key={f.id} value={f.id}>#{f.id} · {f.formulation_type} · {f.target_disease ?? "No target"}</option>
                ))}
              </select>
              {formulations && publishedFormulations.length === 0 && (
                <p className="text-xs text-gray-400 mt-1">No published formulations yet. Publish a formulation to link it here.</p>
              )}
            </div>

            {/* Checklist preview */}
            {checklist && checklist.length > 0 && (
              <div className="bg-forest-50 border border-forest-100 rounded-xl p-4">
                <p className="text-sm font-semibold text-forest-700 mb-3">Required steps for {productType} products:</p>
                <ol className="space-y-2">
                  {checklist.slice(0, 5).map((item, i) => (
                    <li key={i} className="flex gap-2 text-xs text-gray-600">
                      <span className="w-5 h-5 bg-forest-200 text-forest-700 rounded-full flex items-center justify-center font-bold shrink-0 text-[10px]">{item.step ?? i + 1}</span>
                      <span>{item.title ?? item.description}</span>
                    </li>
                  ))}
                  {checklist.length > 5 && (
                    <li className="text-xs text-forest-600 pl-7">+{checklist.length - 5} more steps…</li>
                  )}
                </ol>
              </div>
            )}

            {createMut.isError && <PageError message="Failed to create document. Please try again." />}

            <button type="submit" className="btn-primary w-full py-3 flex items-center justify-center gap-2"
              disabled={createMut.isPending}>
              {createMut.isPending ? <><Spinner /> Creating…</> : "Create Document →"}
            </button>
          </form>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="bg-forest-50 border border-forest-300 text-forest-700 px-4 py-3 rounded-lg text-sm">
            ✅ Document created (Draft). Now let Claude AI generate the content.
          </div>

          <div className="card">
            <div className="flex items-start gap-4 mb-5">
              <span className="text-3xl">🤖</span>
              <div>
                <h3 className="font-bold text-forest-700">AI Auto-Fill</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Claude will generate the full document content including product declaration, ingredient listing,
                  dosage instructions, safety warnings, labeling requirements, and storage conditions.
                </p>
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800 mb-5">
              ⏱️ Generation takes 15–30 seconds. The document will open automatically when ready.
            </div>

            {generateMut.isError && <PageError message="AI generation failed. Check your Anthropic API key." />}

            <div className="flex gap-3">
              <button className="btn-primary flex-1 py-3 flex items-center justify-center gap-2"
                onClick={handleAIGenerate} disabled={generateMut.isPending}>
                {generateMut.isPending ? <><Spinner /> Claude is drafting your document…</> : "🤖 Generate with AI →"}
              </button>
              <button className="btn-outline flex-1 py-3"
                onClick={() => navigate(`/compliance/${docId}`)}>
                Skip (edit manually)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
