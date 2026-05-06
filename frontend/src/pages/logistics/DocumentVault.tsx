import { useState, useRef } from "react";
import { useAllExportDocuments, useGenerateDocument, useUploadDocument } from "../../hooks/useLogistics";
import type { ExportDocument } from "../../hooks/useLogistics";
import { Spinner, Empty, PageError } from "../../components/Layout";

const DOC_TYPE_CONFIG: Record<string, { icon: string; label: string; aiAvailable: boolean }> = {
  invoice:             { icon: "🧾", label: "Commercial Invoice",     aiAvailable: true },
  packing_list:        { icon: "📦", label: "Packing List",           aiAvailable: true },
  coo:                 { icon: "🏴", label: "Certificate of Origin",  aiAvailable: true },
  customs_declaration: { icon: "🛃", label: "Customs Declaration",    aiAvailable: true },
  phytosanitary:       { icon: "🌿", label: "Phytosanitary Cert.",    aiAvailable: false },
  other:               { icon: "📄", label: "Other Document",         aiAvailable: false },
};

function DocCard({
  doc,
  onGenerate,
  onDownload,
}: {
  doc: ExportDocument;
  onGenerate: (doc: ExportDocument) => void;
  onDownload: (doc: ExportDocument) => void;
}) {
  const cfg = DOC_TYPE_CONFIG[doc.document_type] ?? { icon: "📄", label: doc.document_type, aiAvailable: false };

  return (
    <div className="bg-white rounded-xl border border-gray-100 hover:border-forest-200 hover:shadow-sm transition-all p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-forest-50 rounded-lg flex items-center justify-center text-xl flex-shrink-0">
            {cfg.icon}
          </div>
          <div>
            <p className="font-semibold text-gray-800 text-sm">{cfg.label}</p>
            <p className="text-xs text-gray-400">Order #{doc.order_id}</p>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {doc.ai_generated && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
              🤖 AI
            </span>
          )}
          {doc.verified && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-forest-100 text-forest-700">
              ✓ Verified
            </span>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-400">
        Created: {new Date(doc.created_at).toLocaleDateString("en-NG", {
          day: "numeric", month: "short", year: "numeric",
        })}
      </p>

      <div className="flex gap-2 mt-auto pt-2 border-t border-gray-50">
        {doc.file_url ? (
          <button
            onClick={() => onDownload(doc)}
            className="btn-primary text-xs py-1.5 flex-1 flex items-center justify-center gap-1"
          >
            ↓ Download PDF
          </button>
        ) : cfg.aiAvailable ? (
          <button
            onClick={() => onGenerate(doc)}
            className="btn-secondary text-xs py-1.5 flex-1 flex items-center justify-center gap-1"
          >
            🤖 Generate with AI
          </button>
        ) : (
          <span className="text-xs text-gray-400 flex-1 text-center py-1.5">Awaiting upload</span>
        )}
      </div>
    </div>
  );
}

function GenerateDocModal({
  orderId,
  onClose,
}: {
  orderId: number | null;
  onClose: () => void;
}) {
  const [docType, setDocType] = useState<"invoice" | "packing_list" | "coo" | "customs_declaration">("invoice");
  const generateMut = useGenerateDocument();

  async function handleGenerate() {
    if (!orderId) return;
    await generateMut.mutateAsync({ order_id: orderId, document_type: docType });
  }

  const aiDocTypes = Object.entries(DOC_TYPE_CONFIG)
    .filter(([, v]) => v.aiAvailable)
    .map(([k, v]) => ({ key: k as typeof docType, ...v }));

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="bg-forest-600 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-white font-bold">🤖 AI Document Generator</h3>
            <p className="text-forest-200 text-xs mt-0.5">Order #{orderId}</p>
          </div>
          <button onClick={onClose} className="text-forest-200 hover:text-white">✕</button>
        </div>

        {generateMut.isSuccess ? (
          <div className="p-6 text-center space-y-4">
            <div className="text-5xl">✅</div>
            <h4 className="font-bold text-forest-700">Document Generated!</h4>
            <p className="text-gray-500 text-sm">Your {DOC_TYPE_CONFIG[docType]?.label} has been created by AI and is ready to download.</p>
            <button onClick={() => { generateMut.reset(); onClose(); }} className="btn-primary w-full">Close</button>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            <p className="text-sm text-gray-600">
              Select the document you want AI to generate. It will be pre-filled with your order, shipment and buyer details.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {aiDocTypes.map(({ key, icon, label }) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setDocType(key)}
                  className={`p-3 rounded-xl border-2 text-left transition-colors ${
                    docType === key
                      ? "border-forest-500 bg-forest-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <span className="text-xl">{icon}</span>
                  <p className="text-xs font-medium text-gray-700 mt-1">{label}</p>
                </button>
              ))}
            </div>
            {generateMut.isError && (
              <p className="text-red-600 text-sm">⚠️ Generation failed. Please try again.</p>
            )}
            <div className="flex gap-3">
              <button onClick={handleGenerate} className="btn-primary flex-1"
                disabled={generateMut.isPending}>
                {generateMut.isPending ? <><Spinner /> Generating...</> : "🤖 Generate Document"}
              </button>
              <button onClick={onClose} className="btn-outline flex-1">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DocumentVault() {
  const { data: documents, isLoading, isError } = useAllExportDocuments();
  const uploadMut = useUploadDocument();
  const fileRef = useRef<HTMLInputElement>(null);

  const [generateModal, setGenerateModal] = useState<number | null>(null);
  const [uploadOrderId, setUploadOrderId] = useState("");
  const [filterType, setFilterType] = useState("");
  const [filterOrder, setFilterOrder] = useState("");
  const [uploadSuccess, setUploadSuccess] = useState(false);

  function handleDownload(doc: ExportDocument) {
    if (doc.file_url) {
      window.open(doc.file_url, "_blank");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !uploadOrderId) return;
    const fd = new FormData();
    fd.append("file", file);
    fd.append("document_type", "other");
    await uploadMut.mutateAsync({ orderId: Number(uploadOrderId), formData: fd });
    setUploadSuccess(true);
    setTimeout(() => setUploadSuccess(false), 3000);
    e.target.value = "";
  }

  const filtered = documents?.filter((d) => {
    if (filterType && d.document_type !== filterType) return false;
    if (filterOrder && String(d.order_id) !== filterOrder) return false;
    return true;
  });

  // Group by order
  const grouped = filtered?.reduce<Record<number, ExportDocument[]>>((acc, doc) => {
    if (!acc[doc.order_id]) acc[doc.order_id] = [];
    acc[doc.order_id].push(doc);
    return acc;
  }, {});

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;
  if (isError) return <PageError message="Failed to load documents." />;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-5 rounded-2xl flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <span>📂</span> Export Document Vault
          </h1>
          <p className="text-forest-100 text-sm mt-1">
            All your export documents in one place — AI-generated or uploaded
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => { setGenerateModal(0); }}
            className="btn-secondary text-sm flex items-center gap-1"
          >
            🤖 AI Generate Doc
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            className="btn-outline border-white text-white hover:bg-white/10 text-sm"
          >
            ↑ Upload Document
          </button>
        </div>
      </div>

      {/* Upload area */}
      <input ref={fileRef} type="file" accept=".pdf,.jpg,.png" className="hidden" onChange={handleUpload} />

      {/* Upload helper + order ID prompt */}
      {uploadOrderId === "" && (
        <div className="card">
          <h3 className="font-semibold text-gray-700 mb-3">📤 Upload Existing Document</h3>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="label">Order ID</label>
              <input className="input" type="number" placeholder="Enter order ID to attach document"
                value={uploadOrderId}
                onChange={(e) => setUploadOrderId(e.target.value)} />
            </div>
            <button className="btn-primary py-2.5"
              disabled={!uploadOrderId}
              onClick={() => fileRef.current?.click()}>
              {uploadMut.isPending ? <Spinner /> : "↑ Choose File"}
            </button>
          </div>
          {uploadSuccess && (
            <p className="text-xs text-forest-600 mt-2">✅ Document uploaded successfully!</p>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="label">Filter by Type</label>
            <select className="select w-48" value={filterType}
              onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              {Object.entries(DOC_TYPE_CONFIG).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Filter by Order ID</label>
            <input className="input w-36" placeholder="e.g. 42"
              value={filterOrder}
              onChange={(e) => setFilterOrder(e.target.value)} />
          </div>
          {(filterType || filterOrder) && (
            <button className="btn-ghost text-sm"
              onClick={() => { setFilterType(""); setFilterOrder(""); }}>
              ✕ Clear
            </button>
          )}
          <div className="ml-auto text-sm text-gray-500">
            {filtered?.length ?? 0} document{(filtered?.length ?? 0) !== 1 ? "s" : ""}
          </div>
        </div>
      </div>

      {/* Documents by order */}
      {!filtered || filtered.length === 0 ? (
        <Empty icon="📂" title="No documents yet"
          subtitle="Use the AI Generator to create trade documents or upload existing ones." />
      ) : grouped && Object.entries(grouped).map(([orderId, docs]) => (
        <div key={orderId} className="space-y-3">
          <div className="flex items-center gap-3">
            <h3 className="font-bold text-gray-700">Order #{orderId}</h3>
            <div className="flex-1 h-px bg-gray-100" />
            <button
              onClick={() => setGenerateModal(Number(orderId))}
              className="text-xs text-forest-600 hover:text-forest-800 font-medium flex items-center gap-1"
            >
              🤖 Generate for this order
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Show all 4 generatable types, existing or placeholder */}
            {(["invoice","packing_list","coo","customs_declaration","phytosanitary","other"] as const).map((type) => {
              const existing = docs.find((d) => d.document_type === type);
              if (!existing) {
                // Show AI generate placeholder only for AI-available types
                if (!DOC_TYPE_CONFIG[type]?.aiAvailable) return null;
                return (
                  <div key={type}
                    className="border-2 border-dashed border-gray-200 rounded-xl p-4 flex flex-col gap-2 opacity-60 hover:opacity-100 transition-opacity">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gray-50 rounded-lg flex items-center justify-center text-xl">
                        {DOC_TYPE_CONFIG[type].icon}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-500">{DOC_TYPE_CONFIG[type].label}</p>
                        <p className="text-xs text-gray-400">Not created yet</p>
                      </div>
                    </div>
                    <button
                      onClick={() => setGenerateModal(Number(orderId))}
                      className="btn-ghost text-xs py-1.5 w-full border border-dashed border-gray-300"
                    >
                      🤖 Generate with AI
                    </button>
                  </div>
                );
              }
              return (
                <DocCard
                  key={existing.id}
                  doc={existing}
                  onGenerate={() => setGenerateModal(Number(orderId))}
                  onDownload={handleDownload}
                />
              );
            })}
          </div>
        </div>
      ))}

      {/* AI Generate modal */}
      {generateModal !== null && (
        <GenerateDocModal
          orderId={generateModal > 0 ? generateModal : null}
          onClose={() => setGenerateModal(null)}
        />
      )}
    </div>
  );
}
