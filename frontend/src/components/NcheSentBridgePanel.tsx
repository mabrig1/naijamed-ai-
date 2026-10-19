import { useEffect, useState } from "react";
import { api } from "../lib/api";

interface NcheSentSummary {
  schemaVersion: "1.0";
  source: "NcheSent";
  dataset: "synthetic";
  clinicalUse: false;
  modelVersion: string;
  generatedAt: string;
  totalAssessments: number;
  byState: Record<string, number>;
  byRegimen: Record<string, number>;
  byBand: Record<string, number>;
  notice: string;
}

function Distribution({ title, entries }: { title: string; entries: Record<string, number> }) {
  return (
    <div className="rounded-xl bg-forest-50 p-4">
      <h4 className="font-semibold text-forest-900">{title}</h4>
      <ul className="mt-3 space-y-2 text-sm text-gray-700">
        {Object.entries(entries).map(([name, count]) => (
          <li className="flex justify-between gap-3" key={name}>
            <span>{name}</span><strong>{count}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Demonstration bridge only; explicitly NOT a clinical malaria dashboard. */
export default function NcheSentBridgePanel() {
  const [data, setData] = useState<NcheSentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let active = true;
    api.get<NcheSentSummary>("/api/nchesent-bridge")
      .then(({ data: result }) => {
        if (active && result.source === "NcheSent" && result.dataset === "synthetic" &&
            result.clinicalUse === false && result.schemaVersion === "1.0") {
          setData(result);
        } else if (active) {
          setUnavailable(true);
        }
      })
      .catch(() => { if (active) setUnavailable(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  return (
    <section className="rounded-3xl border border-emerald-200 bg-white p-6 shadow-sm" aria-labelledby="nchesent-heading">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-emerald-700">PharmaOS / FORMULARY research network</p>
          <h2 id="nchesent-heading" className="mt-2 text-2xl font-bold text-forest-800">NcheSent malaria research bridge</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
            Cross-platform research demonstration from NcheSent. This feed contains synthetic counts only:
            no real patients, clinical monitoring, resistance estimates, or treatment recommendations.
          </p>
        </div>
        <a href="https://github.com/mabrig1/NcheSent" target="_blank" rel="noreferrer"
           className="rounded-xl border border-emerald-200 px-4 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50">
          NcheSent project ↗
        </a>
      </div>

      {loading && <p role="status" className="mt-5 text-sm text-gray-600">Checking synthetic research integration…</p>}
      {unavailable && !data && (
        <p role="status" className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">
          Research bridge unavailable or not configured. No data has been imported.
          Configure NCHESENT_BASE_URL after NcheSent deployment.
        </p>
      )}
      {data && (
        <div className="mt-6">
          <div className="flex flex-wrap gap-3">
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900">
              Synthetic demo feed connected
            </span>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-900">
              Research only · model {data.modelVersion}
            </span>
          </div>
          <div className="mt-4 rounded-xl bg-forest-800 p-5 text-white">
            <div className="text-sm">Synthetic demo assessments</div>
            <div className="mt-1 text-4xl font-bold">{data.totalAssessments}</div>
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <Distribution title="Fictional states" entries={data.byState} />
            <Distribution title="Example regimens" entries={data.byRegimen} />
            <Distribution title="Unvalidated score bands" entries={data.byBand} />
          </div>
          <p className="mt-4 text-xs leading-5 text-amber-900">{data.notice}</p>
          <p className="mt-1 text-xs text-gray-500">
            Contract v{data.schemaVersion} · source NcheSent · generated {new Date(data.generatedAt).toLocaleString()}
          </p>
        </div>
      )}
    </section>
  );
}
