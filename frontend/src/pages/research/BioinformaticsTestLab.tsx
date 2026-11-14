import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import snapshot from "../../generated/bioinformatics-catalog.json";

type Service = {
  id: string;
  category: string;
  name: string;
  short: string;
  featured?: boolean;
  deliverables: string[];
  tiers: { id: string; name: string; scope: string }[];
};
type Catalog = { services: Service[]; integrity_notice: string };
type ScientificAsset = {
  kind: "compound" | "protein";
  external_id: string;
  name: string;
  source: string;
  source_url: string;
  molecular_formula?: string;
  molecular_weight?: number;
  smiles?: string;
  connectivity_smiles?: string;
  experimental_method?: string;
  resolution_angstrom?: number;
};
type LookupResult = { result: ScientificAsset; scientific_notice: string };
type Mode = {
  level: "Live reference lookup + planning" | "Planning prototype";
  summary: string;
  steps: string[];
  compound: boolean;
  protein: boolean;
};

const SERVICE_MODES: Record<string, Mode> = {
  "scope-consultation": {
    level: "Planning prototype",
    summary: "Draft research questions, methods and the data-readiness checklist without booking a meeting or paying.",
    steps: ["Define research question and expected outputs", "List available datasets and source licenses", "Document ethics and reproducibility requirements"],
    compound: false, protein: false,
  },
  "admet-screening": {
    level: "Live reference lookup + planning",
    summary: "Check a real PubChem compound record and export a descriptor/ADMET methods checklist. No ADMET predictions are calculated yet.",
    steps: ["Verify compound identity, CID and available SMILES", "Record descriptor and toxicity screening methods", "Run validated RDKit/ADMET tools separately before interpreting any scores"],
    compound: true, protein: false,
  },
  "molecular-docking": {
    level: "Live reference lookup + planning",
    summary: "Retrieve public ligand and PDB structure records and prepare a docking manifest. No AutoDock Vina simulation runs in this browser.",
    steps: ["Check ligand and receptor identifiers", "Prepare protonation states and validated receptor/ligand files", "Define grid, controls and docking parameters", "Execute and verify docking on an approved compute worker"],
    compound: true, protein: true,
  },
  "network-pharmacology": {
    level: "Live reference lookup + planning",
    summary: "Validate public identifiers and export Cytoscape node tables. No compound-target or PPI connection is invented.",
    steps: ["Curate verified compound and target identifiers", "Gather source-backed interaction evidence", "Build and validate a compound-target network", "Export verified edges and perform enrichment with appropriate provenance"],
    compound: true, protein: true,
  },
  "publication-figures": {
    level: "Live reference lookup + planning",
    summary: "Export a source-linked reference SVG for figure-layout testing. This is not a molecular rendering or publication-ready analysis.",
    steps: ["Verify source records and figure claims", "Draft clear labels and figure provenance", "Export a reference layout", "Generate validated high-resolution results from scientific visualization software"],
    compound: true, protein: true,
  },
  "thesis-computational-package": {
    level: "Live reference lookup + planning",
    summary: "Plan an integrated study, validate sample public identifiers and export a reproducibility brief. Numerical analysis requires separate engines.",
    steps: ["State objectives, hypotheses and study datasets", "Verify public compound/receptor references", "Document screening, network and docking protocols", "Plan validation, statistics, limitations and ethics"],
    compound: true, protein: true,
  },
  "department-analysis-bundle": {
    level: "Planning prototype",
    summary: "Create a multi-project workflow and requirements checklist for a research department, without subscription or checkout.",
    steps: ["List projects, supervisors and research questions", "Allocate shared methods, datasets and responsibilities", "Plan review gates and reusable reporting templates", "Document data protection and research integrity"],
    compound: false, protein: false,
  },
};

const PUBLIC_NOTICE = "Public database records are research references, not experimental validation, ADMET predictions, docking scores, medical advice or proof of safety or efficacy.";

function safeServiceSummary(service: Service): string {
  return service.id === "scope-consultation"
    ? "Prepare a scientific project scope, research questions, data inventory and reproducibility checklist."
    : service.short;
}
function proposedDeliverables(service: Service) {
  // Do not display sales offers or future commercial commitments during testing.
  return service.deliverables.filter(value => !/quote|payment|receipt|price|paid/i.test(value));
}
function download(filename: string, body: string, type: string) {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
function csvCell(value: string) {
  // Escape CSV formulas even when a provider returns unexpected data.
  const clean = /^[=+\-@\t\r]/.test(value) ? "'" + value : value;
  return '"' + clean.replace(/"/g, '""') + '"';
}
function xmlEscape(value: string) {
  return value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}
function scienceError(error: unknown) {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.detail;
    if (typeof message === "string") return message;
  }
  return "Public science lookup is unavailable. Check the identifier or retry; the planning template still works.";
}

export default function BioinformaticsTestLab() {
  // The catalog snapshot is sufficient for all local test workflows.
  // API failure must never disable test buttons or turn on checkout.
  const [catalog, setCatalog] = useState<Catalog>(snapshot as Catalog);
  const [source, setSource] = useState<"checking" | "connected" | "reference">("checking");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [projectTitle, setProjectTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [compoundName, setCompoundName] = useState("aspirin");
  const [proteinId, setProteinId] = useState("1CRN");
  const [compound, setCompound] = useState<LookupResult | null>(null);
  const [protein, setProtein] = useState<LookupResult | null>(null);
  const [busy, setBusy] = useState<"compound" | "protein" | "">("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const refreshCatalog = useCallback(async () => {
    setSource("checking");
    try {
      const { data } = await axios.get<Catalog>("/api/research-commerce", {
        timeout: 9000, headers: { Accept: "application/json", "Cache-Control": "no-cache" },
      });
      if (!data || !Array.isArray(data.services) || data.services.length !== (snapshot as Catalog).services.length ||
          !data.services.every(item => item.id && Array.isArray(item.deliverables))) {
        throw new Error("Unexpected service catalog response");
      }
      setCatalog(data);
      setSource("connected");
    } catch {
      setCatalog(snapshot as Catalog);
      setSource("reference");
    }
  }, []);
  useEffect(() => { void refreshCatalog(); }, [refreshCatalog]);

  const categories = useMemo(() => {
    const groups = new Map<string, Service[]>();
    for (const item of catalog.services) groups.set(item.category, [...(groups.get(item.category) || []), item]);
    return [...groups.entries()];
  }, [catalog]);
  const selected = catalog.services.find(item => item.id === selectedId) || null;
  const mode = selected ? SERVICE_MODES[selected.id] : null;

  function chooseService(service: Service) {
    setSelectedId(service.id);
    setProjectTitle("");
    setNotes("");
    setCompound(null);
    setProtein(null);
    setError("");
    setMessage("");
    // Bring the accessible test workspace into view after React renders it.
    window.setTimeout(() => document.getElementById("service-test-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" }), 0);
  }

  async function runLookup(kind: "compound" | "protein") {
    const query = (kind === "compound" ? compoundName : proteinId).trim();
    if (!query || query.length > 80 || (kind === "protein" && !/^[a-z0-9]{4}$/i.test(query))) {
      setError(kind === "protein" ? "Enter a valid four-character PDB ID." : "Enter a compound name or PubChem CID (up to 80 characters).");
      return;
    }
    setError("");
    setMessage("");
    setBusy(kind);
    if (kind === "compound") setCompound(null);
    else setProtein(null);
    try {
      // Public read-only lookup: no session, password, order or database write.
      const { data } = await axios.post<LookupResult>("/api/discovery", {
        action: kind === "compound" ? "lookup_compound" : "lookup_protein", query,
      }, { timeout: 30000, headers: { Accept: "application/json", "Content-Type": "application/json" } });
      if (!data?.result?.external_id || !data?.result?.source_url || data.result.kind !== kind) {
        throw new Error("Malformed external scientific reference");
      }
      if (kind === "compound") setCompound(data);
      else setProtein(data);
      setMessage(kind === "compound" ? "PubChem identity lookup completed." : "RCSB PDB structure lookup completed.");
    } catch (e) {
      setError(scienceError(e));
    } finally { setBusy(""); }
  }

  function downloadBrief() {
    if (!selected || !mode) return;
    const lines = [
      "# NigerFlora BioSciences — Test Research Brief", "",
      "Prepared: " + new Date().toISOString(),
      "Selected workflow: " + selected.name,
      "Project: " + (projectTitle.trim() || "Untitled research project"),
      "Testing level: " + mode.level, "",
      "## Current test scope", mode.summary, "",
      "## Methods and reproducibility checklist",
      ...mode.steps.map(step => "- [ ] " + step), "",
      "## Proposed future deliverables",
      ...proposedDeliverables(selected).map(d => "- " + d), "",
      "## Researcher notes", notes.trim() || "No notes provided.", "",
      "## Live public reference checks",
      compound ? ("PubChem: " + compound.result.name + " (CID " + compound.result.external_id + ") — " + compound.result.source_url) : "PubChem: not tested",
      protein ? ("RCSB PDB: " + protein.result.name + " (" + protein.result.external_id + ") — " + protein.result.source_url) : "RCSB PDB: not tested",
      "", "## Scientific limitations",
      PUBLIC_NOTICE,
      "No docking, ADMET, molecular dynamics, clinical evaluation or paid service was performed by this test.",
      "No personal or confidential scientific data should be submitted to public reference services.",
    ];
    download("nigerflora-" + selected.id + "-test-brief.md", lines.join("\n") + "\n", "text/markdown;charset=utf-8");
    setMessage("Test brief downloaded locally. No checkout or order was created.");
  }

  function downloadRecords() {
    if (!selected) return;
    const payload = {
      source: "NigerFlora functionality-first test workspace",
      selected_workflow: selected.id,
      captured_at: new Date().toISOString(),
      scientific_notice: PUBLIC_NOTICE,
      execution: { public_reference_lookup: true, docking_performed: false, admet_prediction_performed: false },
      compound: compound?.result || null, protein: protein?.result || null,
    };
    download("nigerflora-public-references.json", JSON.stringify(payload, null, 2) + "\n", "application/json;charset=utf-8");
  }

  function downloadNetworkNodes() {
    const rows: string[][] = [["id", "label", "type", "source", "source_url"]];
    if (compound) rows.push(["CID:" + compound.result.external_id, compound.result.name, "compound", compound.result.source, compound.result.source_url]);
    if (protein) rows.push(["PDB:" + protein.result.external_id, protein.result.name, "protein_structure", protein.result.source, protein.result.source_url]);
    download("nigerflora-cytoscape-verified-nodes.csv",
      rows.map(row => row.map(csvCell).join(",")).join("\n") + "\n", "text/csv;charset=utf-8");
    setMessage("Cytoscape node table exported. No compound-target interactions have been asserted.");
  }

  function downloadReferenceFigure() {
    const records = [compound?.result, protein?.result].filter((value): value is ScientificAsset => Boolean(value));
    if (!records.length) return;
    const lines = [
      '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="' + (230 + records.length * 92) + '" viewBox="0 0 1100 ' + (230 + records.length * 92) + '">',
      '<rect width="1100" height="100%" fill="#ffffff"/>',
      '<text x="45" y="60" font-family="Arial,sans-serif" font-size="30" fill="#174b37">Public scientific reference records</text>',
      '<text x="45" y="98" font-family="Arial,sans-serif" font-size="16" fill="#52525b">Identifier cards only — no inferred biochemical interactions or numerical predictions</text>',
      ...records.flatMap((r, idx) => [
        '<rect x="40" y="' + (130 + idx * 92) + '" rx="12" width="1020" height="76" fill="#eff8f3" stroke="#b5d2c4"/>',
        '<text x="60" y="' + (162 + idx * 92) + '" font-family="Arial,sans-serif" font-size="20" fill="#174b37">' + xmlEscape(r.name.slice(0, 65)) + ' — ' + xmlEscape(r.external_id) + '</text>',
        '<text x="60" y="' + (188 + idx * 92) + '" font-family="Arial,sans-serif" font-size="13" fill="#475569">' + xmlEscape(r.source + " | " + r.source_url).slice(0, 900) + '</text>',
      ]),
      '<text x="45" y="' + (175 + records.length * 92) + '" font-family="Arial,sans-serif" font-size="14" fill="#64748b">NigerFlora test export; verify original sources before publication.</text>',
      '</svg>',
    ];
    download("nigerflora-source-reference-figure.svg", lines.join("\n"), "image/svg+xml;charset=utf-8");
    setMessage("SVG figure-layout test exported from verified public reference records.");
  }

  return (
    <div className="min-h-screen bg-cream text-gray-900">
      <header className="border-b border-forest-800 bg-forest-900 text-white">
        <nav className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-5 py-4">
          <Link to="/" className="font-bold text-gold-300">🌿 NigerFlora BioSciences</Link>
          <div className="flex gap-3 text-sm">
            <Link to="/explore" className="rounded-lg px-3 py-2 hover:bg-forest-800">Science Explorer</Link>
            <Link to="/login" className="rounded-lg px-3 py-2 hover:bg-forest-800">Researcher login</Link>
          </div>
        </nav>
      </header>
      <section className="bg-forest-800 px-5 py-12 text-white">
        <div className="mx-auto max-w-7xl">
          <div className="inline-block rounded-full bg-gold-400/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gold-300">Stage 1 · Functionality testing · No payment</div>
          <h1 className="mt-4 max-w-4xl text-3xl font-bold md:text-5xl">Test NigerFlora research workflows before launch.</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-forest-100 md:text-lg">
            Open any of the seven research services to explore available tests, verify real scientific identifiers,
            and download a research plan. No service price, payment, account or order is required for public tests.
          </p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-forest-500 px-3 py-2">Real PubChem lookups</span>
            <span className="rounded-full border border-forest-500 px-3 py-2">Real RCSB PDB lookups</span>
            <span className="rounded-full border border-forest-500 px-3 py-2">Research briefs and data exports</span>
            <span className="rounded-full border border-forest-500 px-3 py-2">Payment integration deferred</span>
          </div>
        </div>
      </section>

      <main className="mx-auto max-w-7xl space-y-10 px-5 py-10">
        <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-forest-200 bg-white p-4 text-sm">
          <div role="status" className="text-forest-800">
            <strong>Test workspace ready.</strong>{" "}
            {source === "connected" ? "Live service metadata connected." : source === "checking" ? "Checking service metadata; local testing is available." : "Reference catalog loaded; local testing remains available if the live catalog is offline."}
          </div>
          <button className="btn-outline" type="button" onClick={() => void refreshCatalog()} disabled={source === "checking"}>Check API again</button>
        </section>

        {categories.map(([category, services]) => (
          <section key={category}>
            <h2 className="text-2xl font-bold text-forest-800">{category}</h2>
            <p className="mt-1 text-sm text-gray-500">Choose a workflow to examine its scientific capability and required verification steps.</p>
            <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
              {services.map(service => {
                const test = SERVICE_MODES[service.id];
                return (
                  <article className="card flex h-full flex-col border border-forest-100" key={service.id}>
                    <span className="text-xs font-bold uppercase tracking-wide text-forest-600">{test?.level || "Planning prototype"}</span>
                    <h3 className="mt-2 text-xl font-bold text-gray-900">{service.name}</h3>
                    <p className="mt-3 flex-1 text-sm leading-6 text-gray-600">{safeServiceSummary(service)}</p>
                    <div className="mt-4 rounded-xl bg-cream p-4">
                      <div className="text-xs font-bold uppercase text-gray-500">Planned deliverables</div>
                      <ul className="mt-2 space-y-1.5 text-xs leading-6 text-gray-700">
                        {proposedDeliverables(service).slice(0, 5).map(item => <li key={item}>✓ {item}</li>)}
                      </ul>
                    </div>
                    <button type="button" className="btn-primary mt-5" onClick={() => chooseService(service)}>
                      Test this workflow
                    </button>
                  </article>
                );
              })}
            </div>
          </section>
        ))}

        {selected && mode && (
          <section id="service-test-workspace" aria-label="Service testing workspace"
            className="scroll-mt-24 rounded-3xl border border-forest-200 bg-white p-5 shadow-md md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-forest-600">Open testing workspace · {mode.level}</div>
                <h2 className="mt-2 text-2xl font-bold text-forest-900">{selected.name}</h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-gray-600">{mode.summary}</p>
              </div>
              <button className="btn-outline" type="button" onClick={() => setSelectedId(null)}>Close test</button>
            </div>
            {error && <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</div>}
            {message && <div role="status" className="mt-5 rounded-lg border border-forest-200 bg-forest-50 p-3 text-sm text-forest-800">{message}</div>}
            <div className="mt-7 grid gap-5 md:grid-cols-2">
              <label className="text-sm font-semibold text-gray-700">Research project title
                <input className="input mt-2" maxLength={240} value={projectTitle} onChange={e => setProjectTitle(e.target.value)} placeholder="e.g. Compound-target evidence review" />
              </label>
              <label className="text-sm font-semibold text-gray-700">Study notes (public-safe only)
                <textarea className="input mt-2 min-h-24" maxLength={2500} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Research goals and methodology; no patient or confidential data" />
              </label>
            </div>
            {(mode.compound || mode.protein) && (
              <div className="mt-6 grid gap-5 md:grid-cols-2">
                {mode.compound && (
                  <div className="rounded-xl border border-gray-200 p-4">
                    <h3 className="font-bold text-forest-900">Live compound test</h3>
                    <p className="mt-1 text-xs text-gray-500">PubChem identity lookup, not an ADMET prediction.</p>
                    <label className="mt-3 block text-sm">Compound name or CID
                      <input className="input mt-2" aria-label="Compound name or CID" value={compoundName} maxLength={80} onChange={e => setCompoundName(e.target.value)} />
                    </label>
                    <button className="btn-secondary mt-3" type="button" disabled={busy !== ""} onClick={() => void runLookup("compound")}>
                      {busy === "compound" ? "Checking PubChem…" : "Test compound lookup"}
                    </button>
                    {compound && <div className="mt-3 rounded-lg bg-forest-50 p-3 text-sm">
                      <div className="font-semibold">{compound.result.name} · CID {compound.result.external_id}</div>
                      <div className="mt-1">Formula: {compound.result.molecular_formula || "Not reported"}</div>
                      <a className="mt-1 inline-block text-forest-700 underline" href={compound.result.source_url} target="_blank" rel="noreferrer">View source</a>
                    </div>}
                  </div>
                )}
                {mode.protein && (
                  <div className="rounded-xl border border-gray-200 p-4">
                    <h3 className="font-bold text-forest-900">Live structure test</h3>
                    <p className="mt-1 text-xs text-gray-500">RCSB PDB record lookup, not a docking simulation.</p>
                    <label className="mt-3 block text-sm">PDB structure ID
                      <input className="input mt-2" aria-label="PDB structure ID" value={proteinId} maxLength={4} onChange={e => setProteinId(e.target.value.toUpperCase())} />
                    </label>
                    <button className="btn-secondary mt-3" type="button" disabled={busy !== ""} onClick={() => void runLookup("protein")}>
                      {busy === "protein" ? "Checking RCSB…" : "Test structure lookup"}
                    </button>
                    {protein && <div className="mt-3 rounded-lg bg-forest-50 p-3 text-sm">
                      <div className="font-semibold">{protein.result.name} · PDB {protein.result.external_id}</div>
                      <div className="mt-1">Method: {protein.result.experimental_method || "Not specified"}</div>
                      <a className="mt-1 inline-block text-forest-700 underline" href={protein.result.source_url} target="_blank" rel="noreferrer">View source</a>
                    </div>}
                  </div>
                )}
              </div>
            )}

            <div className="mt-7 rounded-2xl bg-cream p-5">
              <h3 className="font-bold text-forest-900">Verification checklist</h3>
              <ol className="mt-3 space-y-2 text-sm text-gray-700">
                {mode.steps.map((step, i) => <li key={step}><strong>{i + 1}.</strong> {step}</li>)}
              </ol>
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <button type="button" className="btn-primary" onClick={downloadBrief}>Download test research brief</button>
              {(compound || protein) && <button type="button" className="btn-secondary" onClick={downloadRecords}>Export verified reference JSON</button>}
              {selected.id === "network-pharmacology" && (compound || protein) &&
                <button type="button" className="btn-secondary" onClick={downloadNetworkNodes}>Export Cytoscape nodes CSV</button>}
              {selected.id === "publication-figures" && (compound || protein) &&
                <button type="button" className="btn-secondary" onClick={downloadReferenceFigure}>Export source-linked SVG</button>}
            </div>
            <p className="mt-5 text-xs leading-6 text-gray-500">
              {PUBLIC_NOTICE} Local briefs are preparatory and do not represent a completed computational service.
              Sensitive records, saved projects and administrative operations still require authentication.
            </p>
          </section>
        )}
        <section className="rounded-2xl border border-forest-200 bg-forest-50 p-5 text-sm leading-7 text-forest-900">
          <strong>Stage 1 testing status:</strong> public reference lookups and local exports are active test paths.
          Docking, validated ADMET prediction, interaction enrichment and specialized rendering require separate scientific computation services.
          <Link className="ml-2 font-semibold underline" to="/explore">Open the independent science explorer.</Link>
        </section>
      </main>
      <footer className="bg-forest-900 px-6 py-7 text-center text-xs text-forest-200">
        NigerFlora BioSciences · Functionality-first testing · Powered by MABRIG Technologies
      </footer>
    </div>
  );
}
