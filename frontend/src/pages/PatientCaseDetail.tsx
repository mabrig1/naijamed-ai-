import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";

type CaseDetail = {
  id: string;
  urgency: string;
  status: string;
  patient_notice?: string;
  structured_intake?: { symptoms?: Array<{ name?: string }> };
};

export default function PatientCaseDetail() {
  const { id } = useParams();
  const [record, setRecord] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!id) return;
    let active = true;
    api.get<CaseDetail>(`/api/clinical/cases/${encodeURIComponent(id)}`)
      .then(({ data }) => { if (active) setRecord(data); })
      .catch(() => { if (active) setError("This case could not be loaded."); });
    return () => { active = false; };
  }, [id]);
  return <div className="card space-y-4">
    <Link className="text-forest-700 underline" to="/dashboard">← My dashboard</Link>
    <h1 className="text-xl font-bold">Clinical case summary</h1>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {!error && !record && <p role="status">Loading…</p>}
    {record && <>
      <p>Status: {record.status} · Priority: {record.urgency}</p>
      <p>{record.patient_notice || "A licensed clinician must review clinical decisions."}</p>
      <h2 className="font-semibold">Symptoms reported</h2>
      <ul className="list-disc pl-5">{(record.structured_intake?.symptoms || []).map((s, i) =>
        <li key={i}>{s.name || "Unspecified symptom"}</li>)}</ul>
      <p className="text-sm text-gray-600">This record is not a confirmed diagnosis or treatment plan.</p>
    </>}
  </div>;
}
