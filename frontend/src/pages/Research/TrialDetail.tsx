import { useParams, Link } from "react-router-dom";
import { useTrialDetail, useTrialAISummary, useVerifyTrial } from "../../hooks/useResearch";
import { useAuth } from "../../hooks/useAuth";
import { Spinner, PageError } from "../../components/Layout";

const STATUS_STYLE: Record<string, string> = {
  submitted: "bg-blue-100 text-blue-700",
  active:    "bg-forest-100 text-forest-700",
  completed: "bg-gold-100 text-gold-700",
  withdrawn: "bg-gray-100 text-gray-500",
};

export default function TrialDetail() {
  const { id } = useParams<{ id: string }>();
  const trialId = Number(id);
  const { user } = useAuth();
  const { data: trial, isLoading, isError } = useTrialDetail(trialId);
  const summaryMut = useTrialAISummary();
  const verifyMut = useVerifyTrial();

  if (isLoading) return <div className="flex justify-center py-16"><Spinner /></div>;
  if (isError || !trial) return <PageError message="Trial not found." />;

  const canVerify = (user?.role === "admin" || user?.role === "researcher") && !trial.is_verified;

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1">
            <h1 className="text-xl font-bold">{trial.study_title}</h1>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${STATUS_STYLE[trial.status] ?? "bg-gray-100 text-gray-500"}`}>
                {trial.status}
              </span>
              {trial.study_phase && <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full">{trial.study_phase}</span>}
              {trial.is_verified && <span className="text-xs bg-white/20 px-2.5 py-0.5 rounded-full">✅ Verified</span>}
            </div>
          </div>
          {canVerify && (
            <button className="btn-secondary text-sm" onClick={() => verifyMut.mutate(trialId)}
              disabled={verifyMut.isPending}>
              {verifyMut.isPending ? <Spinner /> : "Mark Verified"}
            </button>
          )}
        </div>
      </div>

      {trial.outcome_summary && (
        <div className="card">
          <h2 className="section-title">Abstract</h2>
          <p className="text-gray-700 leading-relaxed">{trial.outcome_summary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="card">
          <h2 className="section-title mb-3">Trial Details</h2>
          <dl className="space-y-2 text-sm">
            {trial.methodology && <><dt className="text-gray-500">Methodology</dt><dd className="font-medium">{trial.methodology}</dd></>}
            {trial.patient_count && <><dt className="text-gray-500">Participants</dt><dd className="font-medium">{trial.patient_count}</dd></>}
            {trial.start_date && <><dt className="text-gray-500">Start Date</dt><dd className="font-medium">{new Date(trial.start_date).toLocaleDateString()}</dd></>}
            {trial.end_date && <><dt className="text-gray-500">End Date</dt><dd className="font-medium">{new Date(trial.end_date).toLocaleDateString()}</dd></>}
            {trial.publication_doi && (
              <><dt className="text-gray-500">DOI</dt><dd className="font-mono text-xs text-forest-600">{trial.publication_doi}</dd></>
            )}
          </dl>
        </div>

        {trial.findings && (
          <div className="card">
            <h2 className="section-title mb-3">Key Findings</h2>
            <p className="text-sm text-gray-700 leading-relaxed">{trial.findings}</p>
          </div>
        )}
      </div>

      {/* AI Summary */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h2 className="section-title">AI Analysis</h2>
          <button className="btn-outline text-sm py-1.5 px-3"
            onClick={() => summaryMut.mutate(trialId)}
            disabled={summaryMut.isPending}>
            {summaryMut.isPending ? <Spinner /> : "🤖 Generate Summary"}
          </button>
        </div>
        {summaryMut.data ? (
          <div className="space-y-3 text-sm">
            <p className="text-gray-700">{summaryMut.data.plain_language_summary}</p>
            <div className="flex gap-4 flex-wrap">
              <span className="text-gray-500">Statistical significance: <b className="text-gray-700">{summaryMut.data.statistical_significance}</b></span>
              <span className={`font-semibold ${summaryMut.data.confidence_level === "high" ? "text-forest-600" : summaryMut.data.confidence_level === "medium" ? "text-amber-600" : "text-gray-500"}`}>
                {summaryMut.data.confidence_level} confidence
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Click "Generate Summary" for an AI plain-language analysis of this trial.</p>
        )}
      </div>

      <div className="flex gap-3 flex-wrap">
        <Link to="/research" className="btn-outline text-sm">← All Trials</Link>
        <Link to="/research/submit" state={{ herbId: trial.herb_id }} className="btn-outline text-sm">Submit Another Trial</Link>
      </div>
    </div>
  );
}
