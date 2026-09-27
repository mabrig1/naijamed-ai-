import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner } from "../components/Layout";

type Point = { time: number; concentration: number };

type PKResult = {
  method: string;
  observations?: Point[];
  curve?: Point[];
  metrics: Record<string, number | null>;
  units: Record<string, string>;
  terminal_points_used?: number;
  warnings?: string[];
  research_notice?: string;
};

type PKRun = {
  id: string;
  kind: "nca" | "simulation";
  title: string;
  review_id?: string | null;
  entry_id?: string | null;
  input: Record<string, unknown>;
  result: PKResult;
  created_at?: string | null;
};

type PKRunsResponse = {
  runs: PKRun[];
  account: {
    is_pro: boolean;
    pk_run_count: number;
    pk_run_limit: number | null;
  };
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function number(value: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseObservations(raw: string): Point[] {
  return raw
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split(/[\t,; ]+/).filter(Boolean))
    .filter((parts) => parts.length >= 2)
    .map(([time, concentration]) => ({ time: Number(time), concentration: Number(concentration) }))
    .filter((row) => Number.isFinite(row.time) && Number.isFinite(row.concentration));
}

function formatMetric(value: number | null | undefined) {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  if (Math.abs(value) >= 1000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) {
    return value.toExponential(3);
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function metricLabel(key: string) {
  const labels: Record<string, string> = {
    cmax: "Cmax",
    tmax: "Tmax",
    clast: "Clast",
    tlast: "Tlast",
    auc_0_last: "AUC₀–last",
    auc_extra: "AUC extrapolated",
    auc_0_inf: "AUC₀–∞",
    percent_auc_extrapolated: "% AUC extrapolated",
    lambda_z: "λz",
    terminal_half_life: "Terminal half-life",
    terminal_r_squared: "Terminal R²",
    mrt_0_last: "MRT₀–last",
    clearance: "Clearance",
    volume_z: "Vz",
    cmax_simulated: "Simulated Cmax",
    tmax_simulated: "Simulated Tmax",
    auc_0_duration: "AUC₀–duration",
  };
  return labels[key] ?? key.replaceAll("_", " ");
}

function SimpleCurve({ points, title }: { points: Point[]; title: string }) {
  const width = 680;
  const height = 280;
  const pad = 42;
  if (points.length < 2) return null;
  const maxX = Math.max(...points.map((p) => p.time), 1);
  const maxY = Math.max(...points.map((p) => p.concentration), 1);
  const sx = (time: number) => pad + (time / maxX) * (width - pad * 2);
  const sy = (concentration: number) => height - pad - (concentration / maxY) * (height - pad * 2);
  const polyline = points.map((p) => `${sx(p.time)},${sy(p.concentration)}`).join(" ");

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-4">
      <div className="mb-3 text-sm font-semibold text-forest-800">{title}</div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title} className="h-auto w-full">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="currentColor" opacity="0.35" />
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="currentColor" opacity="0.35" />
        <polyline points={polyline} fill="none" stroke="currentColor" strokeWidth="3" className="text-forest-600" />
        {points.map((p, index) => (
          <circle key={index} cx={sx(p.time)} cy={sy(p.concentration)} r="3.5" fill="currentColor" className="text-gold-500" />
        ))}
        <text x={width / 2} y={height - 8} textAnchor="middle" fontSize="12">Time</text>
        <text x="12" y={height / 2} textAnchor="middle" fontSize="12" transform={`rotate(-90 12 ${height / 2})`}>Concentration</text>
      </svg>
    </div>
  );
}

export default function FormularyPKPD() {
  const [runsData, setRunsData] = useState<PKRunsResponse | null>(null);
  const [activeRun, setActiveRun] = useState<PKRun | null>(null);
  const [mode, setMode] = useState<"nca" | "simulation">("nca");
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [nca, setNca] = useState({
    title: "PK NCA Run",
    observations: "",
    terminal_points: "3",
    dose: "",
    route: "other",
    time_unit: "h",
    concentration_unit: "mg/L",
    dose_unit: "mg",
  });

  const [simulation, setSimulation] = useState({
    title: "One-compartment Simulation",
    model: "one_compartment_iv_bolus",
    dose: "",
    volume: "",
    elimination_half_life: "",
    duration: "",
    points: "101",
    bioavailability: "1",
    absorption_rate: "",
    time_unit: "h",
    dose_unit: "mg",
    volume_unit: "L",
  });

  async function loadRuns() {
    setLoading(true);
    try {
      const { data } = await api.get<PKRunsResponse>("/api/formulary/pkpd/runs");
      setRunsData(data);
      if (!activeRun && data.runs[0]) setActiveRun(data.runs[0]);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runNca() {
    const observations = parseObservations(nca.observations);
    if (observations.length < 3) {
      setError("Enter at least three valid time/concentration rows.");
      return;
    }
    setAction("nca");
    setError("");
    setMessage("");
    try {
      const dose = nca.dose.trim() ? number(nca.dose) : null;
      const { data } = await api.post<PKRun>("/api/formulary/pkpd/nca", {
        title: nca.title,
        observations,
        terminal_points: Number(nca.terminal_points),
        dose,
        route: nca.route,
        time_unit: nca.time_unit,
        concentration_unit: nca.concentration_unit,
        dose_unit: nca.dose_unit,
      });
      setActiveRun(data);
      setMessage("NCA completed and saved to your Formulary workspace.");
      await loadRuns();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function runSimulation() {
    const dose = number(simulation.dose);
    const volume = number(simulation.volume);
    const halfLife = number(simulation.elimination_half_life);
    const duration = number(simulation.duration);
    if (!dose || !volume || !halfLife || !duration) {
      setError("Dose, volume, half-life and duration must all be positive numbers.");
      return;
    }
    setAction("simulation");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<PKRun>("/api/formulary/pkpd/simulate", {
        title: simulation.title,
        model: simulation.model,
        dose,
        volume,
        elimination_half_life: halfLife,
        duration,
        points: Number(simulation.points),
        bioavailability: Number(simulation.bioavailability),
        absorption_rate: simulation.model === "one_compartment_oral" ? number(simulation.absorption_rate) : null,
        time_unit: simulation.time_unit,
        dose_unit: simulation.dose_unit,
        volume_unit: simulation.volume_unit,
      });
      setActiveRun(data);
      setMessage("Simulation completed and saved.");
      await loadRuns();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  const activePoints = useMemo(
    () => activeRun?.result.observations ?? activeRun?.result.curve ?? [],
    [activeRun],
  );

  if (loading && !runsData) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  if (error && !runsData) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary PK/PD Simulator</div>
            <h1 className="mt-3 text-4xl font-bold">From concentration–time data to interpretable PK metrics.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Run research-grade exploratory NCA or simple one-compartment educational simulations without writing R code.
              Results preserve units, assumptions and warnings so they can be checked before use in a thesis, manuscript or training exercise.
            </p>
          </div>
          <div className="min-w-64 rounded-2xl border border-white/10 bg-white/10 p-5 text-sm">
            <div className="text-xs text-forest-200">Saved PK/PD runs</div>
            <div className="mt-1 text-3xl font-bold text-gold-300">{runsData?.account.pk_run_count ?? 0}</div>
            <div className="mt-2 text-xs text-forest-200">
              {runsData?.account.is_pro
                ? "Unlimited with Formulary Scholar"
                : `Free allowance: ${runsData?.account.pk_run_limit ?? 0} saved runs`}
            </div>
            {!runsData?.account.is_pro && <Link to="/pricing" className="mt-4 block rounded-xl bg-gold-400 px-4 py-2.5 text-center font-bold text-forest-900">Upgrade to Scholar</Link>}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link to="/formulary" className="btn-outline">← Living Literature Review</Link>
        <button className={mode === "nca" ? "btn-primary" : "btn-outline"} onClick={() => setMode("nca")}>Noncompartmental Analysis</button>
        <button className={mode === "simulation" ? "btn-primary" : "btn-outline"} onClick={() => setMode("simulation")}>One-compartment Simulation</button>
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-5">
          {mode === "nca" ? (
            <div className="card">
              <h2 className="text-xl font-bold text-forest-800">Observed-data NCA</h2>
              <p className="mt-2 text-sm leading-6 text-gray-500">
                Paste one time/concentration pair per line. Commas, spaces, semicolons and tabs are accepted.
              </p>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="label">Run title</label>
                  <input className="input" value={nca.title} onChange={(e) => setNca((v) => ({ ...v, title: e.target.value }))} />
                </div>
                <div>
                  <label className="label">Time, concentration data</label>
                  <textarea
                    className="input min-h-52 font-mono text-sm"
                    placeholder={"0, 12.4\n0.5, 10.1\n1, 8.2\n2, 5.4\n4, 2.8"}
                    value={nca.observations}
                    onChange={(e) => setNca((v) => ({ ...v, observations: e.target.value }))}
                  />
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div><label className="label">Time unit</label><input className="input" value={nca.time_unit} onChange={(e) => setNca((v) => ({ ...v, time_unit: e.target.value }))} /></div>
                  <div><label className="label">Concentration unit</label><input className="input" value={nca.concentration_unit} onChange={(e) => setNca((v) => ({ ...v, concentration_unit: e.target.value }))} /></div>
                  <div><label className="label">Terminal points</label><input className="input" type="number" min="3" max="8" value={nca.terminal_points} onChange={(e) => setNca((v) => ({ ...v, terminal_points: e.target.value }))} /></div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div>
                    <label className="label">Route</label>
                    <select className="input" value={nca.route} onChange={(e) => setNca((v) => ({ ...v, route: e.target.value }))}>
                      <option value="other">Other / unspecified</option>
                      <option value="iv">IV</option>
                      <option value="oral">Oral</option>
                    </select>
                  </div>
                  <div><label className="label">Dose, optional</label><input className="input" type="number" min="0" step="any" value={nca.dose} onChange={(e) => setNca((v) => ({ ...v, dose: e.target.value }))} /></div>
                  <div><label className="label">Dose unit</label><input className="input" value={nca.dose_unit} onChange={(e) => setNca((v) => ({ ...v, dose_unit: e.target.value }))} /></div>
                </div>
                <button className="btn-primary w-full" disabled={action === "nca"} onClick={runNca}>{action === "nca" ? "Calculating…" : "Calculate & save NCA"}</button>
              </div>
            </div>
          ) : (
            <div className="card">
              <h2 className="text-xl font-bold text-forest-800">One-compartment simulation</h2>
              <p className="mt-2 text-sm leading-6 text-gray-500">
                Explore how explicit model parameters shape a theoretical concentration–time curve. This does not recommend a human dose.
              </p>
              <div className="mt-5 space-y-4">
                <div><label className="label">Run title</label><input className="input" value={simulation.title} onChange={(e) => setSimulation((v) => ({ ...v, title: e.target.value }))} /></div>
                <div>
                  <label className="label">Model</label>
                  <select className="input" value={simulation.model} onChange={(e) => setSimulation((v) => ({ ...v, model: e.target.value }))}>
                    <option value="one_compartment_iv_bolus">One-compartment IV bolus</option>
                    <option value="one_compartment_oral">One-compartment oral, first-order absorption</option>
                  </select>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div><label className="label">Dose</label><input className="input" type="number" min="0" step="any" value={simulation.dose} onChange={(e) => setSimulation((v) => ({ ...v, dose: e.target.value }))} /></div>
                  <div><label className="label">Volume</label><input className="input" type="number" min="0" step="any" value={simulation.volume} onChange={(e) => setSimulation((v) => ({ ...v, volume: e.target.value }))} /></div>
                  <div><label className="label">Elimination half-life</label><input className="input" type="number" min="0" step="any" value={simulation.elimination_half_life} onChange={(e) => setSimulation((v) => ({ ...v, elimination_half_life: e.target.value }))} /></div>
                  <div><label className="label">Simulation duration</label><input className="input" type="number" min="0" step="any" value={simulation.duration} onChange={(e) => setSimulation((v) => ({ ...v, duration: e.target.value }))} /></div>
                </div>
                {simulation.model === "one_compartment_oral" && (
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div><label className="label">Absorption rate (ka)</label><input className="input" type="number" min="0" step="any" value={simulation.absorption_rate} onChange={(e) => setSimulation((v) => ({ ...v, absorption_rate: e.target.value }))} /></div>
                    <div><label className="label">Bioavailability (0–1)</label><input className="input" type="number" min="0.01" max="1" step="0.01" value={simulation.bioavailability} onChange={(e) => setSimulation((v) => ({ ...v, bioavailability: e.target.value }))} /></div>
                  </div>
                )}
                <div className="grid gap-3 sm:grid-cols-3">
                  <div><label className="label">Time unit</label><input className="input" value={simulation.time_unit} onChange={(e) => setSimulation((v) => ({ ...v, time_unit: e.target.value }))} /></div>
                  <div><label className="label">Dose unit</label><input className="input" value={simulation.dose_unit} onChange={(e) => setSimulation((v) => ({ ...v, dose_unit: e.target.value }))} /></div>
                  <div><label className="label">Volume unit</label><input className="input" value={simulation.volume_unit} onChange={(e) => setSimulation((v) => ({ ...v, volume_unit: e.target.value }))} /></div>
                </div>
                <button className="btn-primary w-full" disabled={action === "simulation"} onClick={runSimulation}>{action === "simulation" ? "Simulating…" : "Simulate & save"}</button>
              </div>
            </div>
          )}

          <div className="card">
            <h3 className="text-lg font-bold text-forest-800">Saved runs</h3>
            <div className="mt-4 max-h-80 space-y-2 overflow-y-auto">
              {runsData?.runs.length ? runsData.runs.map((run) => (
                <button key={run.id} type="button" onClick={() => setActiveRun(run)} className={`w-full rounded-xl border p-3 text-left ${activeRun?.id === run.id ? "border-forest-500 bg-forest-50" : "border-gray-100 hover:border-forest-200"}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold text-gray-900">{run.title}</span>
                    <span className="text-[10px] uppercase text-gray-400">{run.kind}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">{run.created_at ? new Date(run.created_at).toLocaleString() : run.id}</div>
                </button>
              )) : <p className="text-sm text-gray-400">No saved PK/PD runs yet.</p>}
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {activeRun ? (
            <>
              <div className="card">
                <div className="text-xs font-bold uppercase tracking-wide text-forest-500">{activeRun.kind === "nca" ? "NCA result" : "Simulation result"}</div>
                <h2 className="mt-1 text-2xl font-bold text-gray-900">{activeRun.title}</h2>
                <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(activeRun.result.metrics).map(([key, value]) => (
                    <div key={key} className="rounded-xl bg-cream p-4">
                      <div className="text-xs text-gray-500">{metricLabel(key)}</div>
                      <div className="mt-1 text-2xl font-bold text-forest-800">{formatMetric(value)}</div>
                    </div>
                  ))}
                </div>
              </div>

              <SimpleCurve points={activePoints} title={activeRun.kind === "nca" ? "Observed concentration–time profile" : "Simulated concentration–time profile"} />

              {!!activeRun.result.warnings?.length && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
                  <h3 className="font-bold text-amber-800">Interpretation warnings</h3>
                  <ul className="mt-3 space-y-2 text-sm text-amber-900">
                    {activeRun.result.warnings.map((warning) => <li key={warning}>• {warning}</li>)}
                  </ul>
                </div>
              )}

              <div className="rounded-2xl border border-forest-100 bg-white p-5 text-sm leading-6 text-gray-600">
                <strong className="text-forest-800">Units:</strong>{" "}
                {Object.entries(activeRun.result.units).map(([key, value]) => `${key}=${value}`).join(" · ")}
              </div>

              <div className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
                <strong>Research boundary:</strong> {activeRun.result.research_notice ?? "Verify assumptions and units before scientific or clinical interpretation."}
              </div>
            </>
          ) : (
            <div className="card py-20 text-center text-gray-400">Run or select an analysis to view results.</div>
          )}
        </div>
      </section>
    </div>
  );
}
