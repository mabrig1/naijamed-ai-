import { useParams, Link } from "react-router-dom";
import { useComplianceDocument, useGenerateComplianceDocument, useSubmitComplianceDocument } from "../../hooks/useCompliance";
import { Spinner, PageError } from "../../components/Layout";

const STATUS_STYLE: Record<string, string> = {
  draft:     "bg-gray-100 text-gray-600",
  submitted: "bg-blue-100 text-blue-700",
  approved:  "bg-forest-100 text-forest-700",
  rejected:  "bg-red-100 text-red-700",
};

export default function DocumentDetail() {
  const { id } = useParams<{ id: string }>();
  const docId = Number(id);
  const { data: doc, isLoading, isError } = useComplianceDocument(docId);
  const generateMut = useGenerateComplianceDocument();
  const submitMut = useSubmitComplianceDocument();

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;
  if (isError || !doc) return <PageError message="Document not found." />;

  const content = doc.content_json as Record<string, unknown> | null;
  const hasContent = content && Object.keys(content).length > 0;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h1 className="text-xl font-bold capitalize">
              {doc.product_name ?? doc.document_type.replace(/_/g, " ")}
            </h1>
            {doc.product_type && <p className="text-forest-200 text-sm capitalize mt-0.5">{doc.product_type} product</p>}
            <div className="flex gap-2 mt-2">
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${STATUS_STYLE[doc.status] ?? "bg-gray-100"}`}>
                {doc.status}
              </span>
              {doc.nafdac_stage && (
                <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full font-mono">
                  Ref: {doc.nafdac_stage}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            {doc.status === "draft" && (
              <>
                {!hasContent && (
                  <button className="btn-secondary text-sm" onClick={() => generateMut.mutate(docId)}
                    disabled={generateMut.isPending}>
                    {generateMut.isPending ? <Spinner /> : "🤖 AI Generate"}
                  </button>
                )}
                <button className="btn-outline border-white text-white hover:bg-white/10 text-sm"
                  onClick={() => submitMut.mutate(docId)} disabled={submitMut.isPending || !hasContent}>
                  {submitMut.isPending ? <Spinner /> : "Submit to NAFDAC"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {!hasContent && doc.status === "draft" && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          ⚠️ This document has no content yet. Click <b>AI Generate</b> to let Claude draft the content automatically, or edit manually.
        </div>
      )}

      {generateMut.isError && <PageError message="AI generation failed. Please try again." />}
      {submitMut.isError && <PageError message="Submission failed. Ensure the document has content." />}
      {submitMut.isSuccess && (
        <div className="bg-forest-50 border border-forest-300 text-forest-700 px-4 py-3 rounded-lg text-sm">
          ✅ Document submitted to NAFDAC successfully.
        </div>
      )}

      {hasContent && (
        <div className="card space-y-4">
          <h2 className="section-title">Document Content</h2>
          {Object.entries(content).map(([key, value]) => (
            <div key={key} className="border-b border-gray-50 pb-3 last:border-0 last:pb-0">
              <h3 className="text-sm font-semibold text-forest-700 capitalize mb-1">
                {key.replace(/_/g, " ")}
              </h3>
              {Array.isArray(value) ? (
                <ul className="space-y-1">
                  {(value as string[]).map((item, i) => (
                    <li key={i} className="text-sm text-gray-600 flex gap-2">
                      <span className="text-forest-400 shrink-0">•</span> {item}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{String(value)}</p>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-3">
        <Link to="/compliance" className="btn-outline text-sm">← All Documents</Link>
        <Link to="/compliance/chat" className="btn-outline text-sm">💬 Ask NAFDAC Assistant</Link>
      </div>
    </div>
  );
}
