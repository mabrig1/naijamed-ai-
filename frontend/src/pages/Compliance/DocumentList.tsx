import { Link } from "react-router-dom";
import { useComplianceDocuments, useNafdacStages } from "../../hooks/useCompliance";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { ComplianceDocument, NafdacStage } from "../../types";

const STATUS_STYLE: Record<string, string> = {
  draft:      "bg-gray-100 text-gray-600",
  submitted:  "bg-blue-100 text-blue-700",
  approved:   "bg-forest-100 text-forest-700",
  rejected:   "bg-red-100 text-red-700",
};

function DocumentCard({ doc }: { doc: ComplianceDocument }) {
  return (
    <Link to={`/compliance/${doc.id}`} className="card-hover block group">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h3 className="font-bold text-forest-700 group-hover:underline">
            {doc.product_name ?? doc.document_type.replace(/_/g, " ")}
          </h3>
          {doc.product_type && (
            <p className="text-xs text-gray-500 capitalize">{doc.product_type}</p>
          )}
        </div>
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ml-2 shrink-0 ${STATUS_STYLE[doc.status] ?? "bg-gray-100 text-gray-500"}`}>
          {doc.status}
        </span>
      </div>

      <p className="text-sm text-gray-500 capitalize mb-3">
        📄 {doc.document_type.replace(/_/g, " ")}
      </p>

      {doc.nafdac_stage && (
        <p className="text-xs font-mono text-forest-600 bg-forest-50 px-2 py-1 rounded inline-block mb-3">
          Ref: {doc.nafdac_stage}
        </p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-gray-100 text-xs text-gray-400">
        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
        {doc.submitted_at && (
          <span>Submitted: {new Date(doc.submitted_at).toLocaleDateString()}</span>
        )}
      </div>
    </Link>
  );
}

function StageTimeline({ stages }: { stages: NafdacStage[] }) {
  return (
    <div className="relative">
      {stages.map((stage, i) => (
        <div key={i} className="flex gap-4 pb-4">
          <div className="flex flex-col items-center">
            <div className="w-7 h-7 rounded-full bg-forest-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
              {stage.stage_number ?? i + 1}
            </div>
            {i < stages.length - 1 && <div className="w-0.5 flex-1 bg-forest-200 mt-1" />}
          </div>
          <div className="pb-2">
            <p className="font-semibold text-sm text-gray-800">{stage.name}</p>
            <p className="text-xs text-gray-500">
              ⏱️ {stage.typical_duration}
              {stage.fees_approximate ? ` · ${stage.fees_approximate}` : ""}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DocumentList() {
  const { data: documents, isLoading, isError } = useComplianceDocuments();
  const { data: stagesData } = useNafdacStages("herbal");

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">📋 NAFDAC Compliance</h1>
          <p className="text-forest-200 text-sm mt-1">AI-assisted regulatory documents for Nigerian herb products</p>
        </div>
        <div className="flex gap-3">
          <Link to="/compliance/chat" className="btn-outline border-white text-white hover:bg-white/10 text-sm">💬 Chat Assistant</Link>
          <Link to="/compliance/create" className="btn-secondary text-sm">➕ New Document</Link>
        </div>
      </div>

      {/* Stats */}
      {documents && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(["draft", "submitted", "approved", "rejected"] as const).map((s) => (
            <div key={s} className="card text-center py-3">
              <div className="text-2xl font-bold text-forest-700">{documents.filter((d) => d.status === s).length}</div>
              <div className="text-xs text-gray-500 capitalize">{s}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {isLoading && <div className="flex justify-center py-12"><Spinner /></div>}
          {isError && <PageError message="Failed to load compliance documents." />}
          {!isLoading && documents?.length === 0 && (
            <Empty icon="📋" title="No documents yet" subtitle="Create your first NAFDAC compliance document." />
          )}
          {!isLoading && documents && documents.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {documents.map((doc) => <DocumentCard key={doc.id} doc={doc} />)}
            </div>
          )}
        </div>

        {/* NAFDAC stages sidebar */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="font-semibold text-forest-700 mb-4">NAFDAC Approval Stages</h3>
            {stagesData?.stages ? (
              <StageTimeline stages={stagesData.stages} />
            ) : (
              <p className="text-sm text-gray-400">Loading stages…</p>
            )}
            {stagesData?.general_notes && stagesData.general_notes.length > 0 && (
              <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg space-y-1">
                {stagesData.general_notes.map((note, i) => (
                  <p key={i} className="text-xs text-amber-700">• {note}</p>
                ))}
              </div>
            )}
          </div>
          <Link to="/compliance/chat" className="card bg-forest-50 border-forest-200 block hover:shadow-md transition-shadow">
            <h3 className="font-semibold text-forest-700 mb-1">💬 NAFDAC AI Assistant</h3>
            <p className="text-sm text-gray-600">Ask any question about the regulatory process, requirements, or compliance checklist.</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
