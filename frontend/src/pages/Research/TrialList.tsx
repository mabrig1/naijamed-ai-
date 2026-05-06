import { Link } from "react-router-dom";
import { useTrialList, useVerifyTrial } from "../../hooks/useResearch";
import { useHerbList } from "../../hooks/useHerbs";
import { useAuth } from "../../hooks/useAuth";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { ClinicalTrial, TrialStatus } from "../../types";
import { useState } from "react";

const STATUS_STYLE: Record<string, string> = {
  submitted:  "bg-blue-100 text-blue-700",
  active:     "bg-forest-100 text-forest-700",
  completed:  "bg-gold-100 text-gold-700",
  withdrawn:  "bg-gray-100 text-gray-500",
};

function TrialCard({ trial, canVerify, onVerify }: { trial: ClinicalTrial; canVerify: boolean; onVerify: (id: number) => void }) {
  return (
    <Link to={`/research/trials/${trial.id}`} className="card-hover block group">
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-bold text-forest-700 group-hover:underline line-clamp-1">{trial.study_title}</h3>
        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ml-2 shrink-0 ${STATUS_STYLE[trial.status] ?? "bg-gray-100 text-gray-500"}`}>
          {trial.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-gray-500 mb-3">
        {trial.study_phase && <span className="bg-gray-100 px-2 py-0.5 rounded">{trial.study_phase}</span>}
        {trial.patient_count && <span>👥 {trial.patient_count} participants</span>}
        {trial.is_verified && <span className="text-forest-600 font-semibold">✅ Verified</span>}
      </div>

      {trial.outcome_summary && (
        <p className="text-sm text-gray-600 line-clamp-2 mb-3">{trial.outcome_summary}</p>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-gray-100 text-xs text-gray-400">
        <span>{new Date(trial.created_at).toLocaleDateString()}</span>
        {canVerify && !trial.is_verified && (
          <button
            onClick={(e) => { e.preventDefault(); onVerify(trial.id); }}
            className="text-xs btn-outline py-1 px-3 border-forest-400 text-forest-600"
          >
            Mark Verified
          </button>
        )}
      </div>
    </Link>
  );
}

export default function TrialList() {
  const { user } = useAuth();
  const [statusFilter, setStatusFilter] = useState<TrialStatus | "">("");
  const [herbFilter, setHerbFilter] = useState("");
  const { data: trials, isLoading, isError } = useTrialList({
    status: statusFilter || undefined,
    herb_id: herbFilter ? Number(herbFilter) : undefined,
  });
  const { data: herbs } = useHerbList({ limit: 100 });
  const verifyMut = useVerifyTrial();

  const canVerify = user?.role === "admin" || user?.role === "researcher";

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">🔬 Clinical Trials</h1>
          <p className="text-forest-200 text-sm mt-1">Evidence-based research on Nigerian medicinal herbs</p>
        </div>
        <div className="flex gap-3">
          <Link to="/research/evidence" className="btn-outline border-white text-white hover:bg-white/10 text-sm">🧬 Herb Evidence</Link>
          <Link to="/research/submit" className="btn-secondary text-sm">➕ Submit Trial</Link>
        </div>
      </div>

      {/* Stats */}
      {trials && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(["submitted", "active", "completed", "withdrawn"] as const).map((s) => (
            <div key={s} className="card text-center py-3">
              <div className="text-2xl font-bold text-forest-700">{trials.filter((t) => t.status === s).length}</div>
              <div className="text-xs text-gray-500 capitalize">{s}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Filter by Status</label>
            <select className="select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as TrialStatus | "")}>
              <option value="">All statuses</option>
              <option value="submitted">Submitted</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="withdrawn">Withdrawn</option>
            </select>
          </div>
          <div>
            <label className="label">Filter by Herb</label>
            <select className="select" value={herbFilter} onChange={(e) => setHerbFilter(e.target.value)}>
              <option value="">All herbs</option>
              {herbs?.map((h) => <option key={h.id} value={h.id}>{h.name_english}</option>)}
            </select>
          </div>
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-12"><Spinner /></div>}
      {isError && <PageError message="Failed to load clinical trials." />}
      {!isLoading && trials?.length === 0 && (
        <Empty icon="🔬" title="No trials found" subtitle="Be the first to submit a clinical trial for this herb." />
      )}

      {!isLoading && trials && trials.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {trials.map((trial) => (
            <TrialCard
              key={trial.id}
              trial={trial}
              canVerify={canVerify}
              onVerify={(id) => verifyMut.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
