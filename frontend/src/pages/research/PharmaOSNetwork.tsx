import { useState } from "react";
import { Link } from "react-router-dom";

type Candidate = {
  name: string; mentions: number; rationale: string; safety: string;
  pubchem: null | {
    cid: number; formula: string | null; molecularWeight: number | null;
    xlogp: number | null; tpsa: number | null; donors: number | null;
    acceptors: number | null; sourceUrl: string; lipinskiViolations: number;
  };
};
type DiscoveryBundle = {
  schemaVersion: string; researchOnly: true; clinicalUse: false;
  source: { name: string; sha256: string };
  compounds: Candidate[];
  agents: Array<{ id: number; role: string; status: string }>;
  summary: { molecularDockingPerformed: false; admetPredictionPerformed: false };
};

function isBundle(value: unknown): value is DiscoveryBundle {
  if (!value || typeof value !== "object") return false;
  const d = value as Record<string, unknown>;
  const s = d.source as Record<string, unknown> | undefined;
  const sum = d.summary as Record<string, unknown> | undefined;
  if (d.schemaVersion !== "discovery-1.0" || d.researchOnly !== true || d.clinicalUse !== false ||
      !s || typeof s.name !== "string" || typeof s.sha256 !== "string" ||
      !/^[a-f0-9]{64}$/i.test(s.sha256) ||
      !sum || sum.molecularDockingPerformed !== false || sum.admetPredictionPerformed !== false ||
      !Array.isArray(d.compounds) || d.compounds.length > 50 ||
      !Array.isArray(d.agents) || d.agents.length > 50) return false;
  return d.compounds.every((c: Candidate) => c && typeof c.name === "string" &&
    c.name.length > 1 && c.name.length < 100 &&
    (c.pubchem === null || (typeof c.pubchem === "object" && Number.isInteger(c.pubchem.cid) && c.pubchem.cid > 0)));
}

const pretty = (value: number | null | undefined) => typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "N/A";

export default function PharmaOSNetwork() {
  const [bundle, setBundle] = useState<DiscoveryBundle | null>(null);
  const [error, setError] = useState("");
  const [order, setOrder] = useState<"name" | "weight">("name");

  async function read(file?: File) {
    setBundle(null); setError("");
    if (!file) return;
    try {
      if (file.size > 300_000) throw new Error("Import limit: 300 KB.");
      const data: unknown = JSON.parse(await file.text());
      if (!isBundle(data)) throw new Error("This is not a validated, research-only PharmaOS discovery report.");
      setBundle(data);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Invalid report."); }
  }

  const compounds = [...(bundle?.compounds ?? [])].sort((a, b) =>
    order === "name" ? a.name.localeCompare(b.name) : (a.pubchem?.molecularWeight ?? Number.POSITIVE_INFINITY) - (b.pubchem?.molecularWeight ?? Number.POSITIVE_INFINITY));

  return <main className="min-h-screen bg-cream text-forest-900">
    <section className="bg-forest-800 px-5 py-8 text-white">
      <div className="mx-auto max-w-6xl">
        <nav className="flex flex-wrap gap-4 text-sm text-gold-300">
          <Link to="/">NigerFlora home</Link>
          <a href="https://nchesent.mabrigkorie.org/pharmaos" rel="noreferrer">NcheSent PharmaOS</a>
          <a href="https://statlab.mabrigkorie.org/pharmaos.html" rel="noreferrer">StatLab handoff</a>
          <a href="https://scholar.mabrigkorie.org/pharmaos" rel="noreferrer">Scholar publishing handoff</a>
        </nav>
        <p className="mt-10 text-xs font-bold uppercase tracking-widest text-gold-300">MABRIG PharmaOS Network · NigerFlora</p>
        <h1 className="mt-3 text-4xl font-bold">Molecular Evidence Review</h1>
        <p className="mt-4 max-w-3xl text-forest-100">
          Import the validated NcheSent research bundle and inspect public chemical descriptors.
          Continue to NigerFlora's existing compound explorer, protected discovery workstation or research services.
          Files stay inside your browser during this handoff.
        </p>
      </div>
    </section>
    <div className="mx-auto max-w-6xl space-y-6 px-5 py-8">
      <section className="rounded-2xl border border-forest-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-widest text-forest-700">Existing computational demonstration</p>
        <h2 className="mt-2 text-2xl font-bold">1,128-compound solubility benchmark</h2>
        <p className="mt-2 text-sm text-gray-600">
          Run the existing molecular-property model and inspect its cross-validated predictions
          against published measured water-solubility values. The results include successes and
          substantial prediction errors. Solubility modelling does not prove therapeutic efficacy.
        </p>
        <a href="/assets/solubility-lab.html?v=1f05cdd"
          className="mt-4 inline-block rounded-xl bg-forest-700 px-5 py-3 font-bold text-white">
          Launch real solubility benchmark
        </a>
        <p className="mt-3 text-xs text-gray-500">Existing, separate calculation; the NcheSent paper-import workflow does not yet retrain or call this model.</p>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold">1. Import PharmaOS report</h2>
        <p className="my-2 text-sm text-gray-600">Use the JSON exported by NcheSent's PharmaOS Studio. No personal or clinical data is accepted.</p>
        <input type="file" accept=".json,application/json" aria-label="Import PharmaOS research bundle" onChange={(e) => void read(e.target.files?.[0])} className="mt-3 block w-full" />
        {error && <p role="alert" className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-red-800">{error}</p>}
      </section>
      {bundle && <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold">2. Molecular descriptor review</h2>
        <p className="mt-2 text-sm">Document: {bundle.source.name} · {bundle.compounds.length} identified names · {bundle.agents.filter((a) => a.status === "completed").length} completed agent tasks</p>
        <p className="mt-2 break-all text-xs text-gray-500">Original text SHA-256: {bundle.source.sha256}</p>
        <label htmlFor="sort-molecules" className="mt-5 block font-semibold">Sort candidates by</label>
        <select id="sort-molecules" value={order} onChange={(e) => setOrder(e.target.value as "name" | "weight")} className="mt-2 rounded-lg border p-2">
          <option value="name">Compound name</option><option value="weight">Molecular weight (if available)</option>
        </select>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {compounds.map((compound) => <article key={compound.name} className="rounded-xl border border-gray-200 p-5">
            <h3 className="text-lg font-bold capitalize">{compound.name}</h3>
            <p className="my-2 text-sm">{compound.rationale}</p>
            {compound.pubchem ? <>
              <p className="text-sm">Formula: {compound.pubchem.formula ?? "N/A"}</p>
              <p className="text-sm">Molecular weight: {pretty(compound.pubchem.molecularWeight)} · XLogP: {pretty(compound.pubchem.xlogp)}</p>
              <p className="text-sm">TPSA: {pretty(compound.pubchem.tpsa)} · Rule-of-five descriptor flags: {compound.pubchem.lipinskiViolations}</p>
              <a className="mt-2 inline-block text-sm font-semibold text-forest-700 underline" target="_blank" rel="noreferrer"
                href={"https://pubchem.ncbi.nlm.nih.gov/compound/" + compound.pubchem.cid}>Review PubChem CID {compound.pubchem.cid}</a>
            </> : <p className="text-sm text-amber-800">No verified molecular metadata available.</p>}
            <p className="mt-3 text-sm text-amber-900"><strong>Safety note:</strong> {compound.safety}</p>
          </article>)}
        </div>
        <div className="mt-5 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">
          Reusing a PubChem lookup is not an independent experimental verification. No docking, ADMET model,
          pharmacological assay or clinical evaluation was performed in this import workflow.
        </div>
      </section>}
      <section className="rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold">3. Continue actual NigerFlora tools</h2>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link to="/explore" className="rounded-xl bg-forest-700 px-5 py-3 font-bold text-white">Launch public molecular explorer</Link>
          <Link to="/discovery" className="rounded-xl border border-forest-700 px-5 py-3 font-bold text-forest-800">Open protected discovery workspace</Link>
          <Link to="/research-studio" className="rounded-xl border border-forest-700 px-5 py-3 font-bold text-forest-800">Research services and planning</Link>
        </div>
        <p className="mt-4 text-sm text-gray-600">Protected tools require NigerFlora authentication. The import does not create accounts, submit payments, or automatically feed an unverified compound into computational jobs.</p>
      </section>
    </div>
  </main>;
}
