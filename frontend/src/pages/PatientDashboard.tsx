import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

type CaseSummary = {
  id: string;
  urgency: string;
  status: string;
  created_at: string | null;
};

export default function PatientDashboard() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.get<CaseSummary[]>("/api/clinical/my-cases")
      .then(({ data }) => { if (active) setCases(data); })
      .catch(() => { if (active) setError("Unable to load your clinical history. Please try again later."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <section className="space-y-6" aria-label="Patient health dashboard">
      <div className="card border border-forest-100">
        <h2 className="text-xl font-bold text-forest-800">My health overview</h2>
        <p className="mt-2 text-sm text-gray-600">
          Review your own clinical intake history. Assessments are not confirmed diagnoses or prescriptions.
        </p>
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="note">
          For severe or rapidly worsening symptoms, seek emergency medical care immediately. Do not wait for this dashboard.
        </p>
      </div>
      <div className="card">
        <h3 className="text-lg font-semibold text-forest-700">My clinical cases</h3>
        {loading && <p role="status" className="mt-3 text-sm">Loading your cases…</p>}
        {error && <p role="alert" className="mt-3 text-sm text-red-700">{error}</p>}
        {!loading && !error && cases.length === 0 && (
          <p className="mt-3 text-sm text-gray-600">No clinical cases recorded yet.</p>
        )}
        {!loading && !error && cases.length > 0 && (
          <ul className="mt-4 space-y-3">
            {cases.map((item) => (
              <li key={item.id} className="rounded-lg border border-gray-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-gray-800">Case {item.id.slice(0, 8)}</span>
                  <span className="text-xs text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleDateString() : "Date unavailable"}</span>
                </div>
                <p className="mt-1 text-sm text-gray-600">Status: {item.status.replace(/_/g, " ")} · Priority: {item.urgency}</p>
                <Link className="mt-2 inline-block text-sm font-medium text-forest-700 underline" to={`/patient/cases/${encodeURIComponent(item.id)}`}>View my case</Link>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="text-sm text-gray-500">Appointments, prescriptions and laboratory results will appear only after verified clinical integrations are available.</p>
    </section>
  );
}
