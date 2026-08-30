import { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { PageError, Spinner, StatusBadge } from "../../components/Layout";

type Asset = {
  id?: string;
  kind: "compound" | "protein";
  external_id: string;
  name: string;
  source?: string;
  source_url?: string;
  image_url?: string;
  molecular_formula?: string;
  molecular_weight?: number | string;
  canonical_smiles?: string;
  inchikey?: string;
  experimental_method?: string;
  resolution_angstrom?: number;
  polymer_entity_count?: number;
};

type ScreeningJob = {
  id: string;
  title: string;
  status: string;
  created_at?: string;
  manifest: {
    manifest_version: string;
    engine: string;
    execution_mode: string;
    receptor: { pdb_id: string; source: string };
    ligands: { pubchem_cid: string; source: string }[];
    parameters: Record<string, number>;
    scientific_notice: string;
  };
};

type NetworkNode = { id: string; label: string; type?: string };
type NetworkEdge = { source: string; target: string; relation?: string; evidence?: string };
type SavedNetwork = {
  id: string;
  title: string;
  status: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  created_at?: string;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function parseNetwork(nodesText: string, edgesText: string): { nodes: NetworkNode[]; edges: NetworkEdge[] } {
  const nodes = nodesText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [id, label, type] = line.split("|").map((part) => part.trim());
      return { id, label: label || id, type: type || "entity" };
    })
    .filter((node) => node.id);

  const edges = edgesText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [source, target, relation, evidence] = line.split("|").map((part) => part.trim());
      return { source, target, relation: relation || "associated_with", evidence: evidence || "" };
    })
    .filter((edge) => edge.source && edge.target);

  return { nodes, edges };
}

function NetworkPreview({ nodes, edges }: { nodes: NetworkNode[]; edges: NetworkEdge[] }) {
  const width = 760;
  const height = 360;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) * 0.34;
  const positioned = nodes.map((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(nodes.length, 1) - Math.PI / 2;
    return { ...node, x: centerX + Math.cos(angle) * radius, y: centerY + Math.sin(angle) * radius };
  });
  const byId = new Map(positioned.map((node) => [node.id, node]));

  if (!nodes.length) {
    return <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">Add nodes to preview the interaction network.</div>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white p-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="min-w-[620px] w-full" role="img" aria-label="Interaction network preview">
        {edges.map((edge, index) => {
          const source = byId.get(edge.source);
          const target = byId.get(edge.target);
          if (!source || !target) return null;
          return <line key={`${edge.source}-${edge.target}-${index}`} x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#9ca3af" strokeWidth="2" />;
        })}
        {positioned.map((node) => (
          <g key={node.id}>
            <circle cx={node.x} cy={node.y} r="25" fill={node.type === "compound" ? "#d4a72c" : node.type === "protein" ? "#1f6b4f" : "#6b7280"} />
            <text x={node.x} y={node.y + 4} textAnchor="middle" fontSize="11" fill="white" fontWeight="700">{node.id.slice(0, 8)}</text>
            <text x={node.x} y={node.y + 42} textAnchor="middle" fontSize="11" fill="#374151">{node.label.slice(0, 24)}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

export default function DiscoveryWorkbench() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [jobs, setJobs] = useState<ScreeningJob[]>([]);
  const [networks, setNetworks] = useState<SavedNetwork[]>([]);
  const [compoundQuery, setCompoundQuery] = useState("");
  const [proteinQuery, setProteinQuery] = useState("");
  const [compoundResult, setCompoundResult] = useState<Asset | null>(null);
  const [proteinResult, setProteinResult] = useState<Asset | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const compounds = assets.filter((asset) => asset.kind === "compound");
  const proteins = assets.filter((asset) => asset.kind === "protein");

  const [screening, setScreening] = useState({
    title: "",
    receptor_id: "",
    ligand_ids: [] as string[],
    center_x: "0",
    center_y: "0",
    center_z: "0",
    size_x: "20",
    size_y: "20",
    size_z: "20",
    exhaustiveness: "8",
    num_modes: "9",
    seed: "0",
  });

  const [networkTitle, setNetworkTitle] = useState("Polyherbal interaction evidence network");
  const [nodesText, setNodesText] = useState("compound-1|Plant compound|compound\ntarget-1|Candidate target|protein");
  const [edgesText, setEdgesText] = useState("compound-1|target-1|predicted_interaction|Add database or study evidence here");
  const parsedNetwork = useMemo(() => parseNetwork(nodesText, edgesText), [nodesText, edgesText]);

  async function loadWorkspace() {
    setBusy("load");
    setError("");
    try {
      const [libraryResponse, jobsResponse, networksResponse] = await Promise.all([
        api.post("/api/discovery", { action: "library" }),
        api.post("/api/discovery", { action: "my_screening_jobs" }),
        api.post("/api/discovery", { action: "my_networks" }),
      ]);
      setAssets(libraryResponse.data.assets ?? []);
      setJobs(jobsResponse.data.jobs ?? []);
      setNetworks(networksResponse.data.networks ?? []);
    } catch (err) {
      setError(detail(err));
    } finally {
      setBusy("");
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, []);

  async function lookup(kind: "compound" | "protein") {
    setBusy(kind);
    setError("");
    setNotice("");
    try {
      const query = kind === "compound" ? compoundQuery : proteinQuery;
      const response = await api.post("/api/discovery", { action: kind === "compound" ? "lookup_compound" : "lookup_protein", query });
      if (kind === "compound") setCompoundResult(response.data.result);
      else setProteinResult(response.data.result);
      setNotice(response.data.scientific_notice ?? "");
    } catch (err) {
      setError(detail(err));
    } finally {
      setBusy("");
    }
  }

  async function saveAsset(asset: Asset) {
    setBusy(`save-${asset.kind}`);
    setError("");
    try {
      await api.post("/api/discovery", { action: "save_asset", asset });
      setNotice(`${asset.name} saved to your discovery library.`);
      await loadWorkspace();
    } catch (err) {
      setError(detail(err));
    } finally {
      setBusy("");
    }
  }

  function toggleLigand(cid: string) {
    setScreening((value) => ({
      ...value,
      ligand_ids: value.ligand_ids.includes(cid) ? value.ligand_ids.filter((id) => id !== cid) : [...value.ligand_ids, cid],
    }));
  }

  async function createScreeningJob() {
    setBusy("screening");
    setError("");
    try {
      const parameters = Object.fromEntries(
        ["center_x", "center_y", "center_z", "size_x", "size_y", "size_z", "exhaustiveness", "num_modes", "seed"].map((key) => [key, screening[key as keyof typeof screening]])
      );
      const response = await api.post("/api/discovery", {
        action: "create_screening_job",
        title: screening.title,
        receptor_id: screening.receptor_id,
        ligand_ids: screening.ligand_ids,
        parameters,
      });
      setNotice(response.data.message);
      await loadWorkspace();
    } catch (err) {
      setError(detail(err));
    } finally {
      setBusy("");
    }
  }

  async function saveNetwork() {
    setBusy("network");
    setError("");
    try {
      const response = await api.post("/api/discovery", {
        action: "save_network",
        title: networkTitle,
        nodes: parsedNetwork.nodes,
        edges: parsedNetwork.edges,
      });
      setNotice(`Network ${response.data.network.id} saved as hypothesis-generating evidence.`);
      await loadWorkspace();
    } catch (err) {
      setError(detail(err));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-3xl bg-forest-800 px-6 py-9 text-white shadow-xl md:px-10">
        <div className="grid gap-8 lg:grid-cols-[1.4fr_0.8fr] lg:items-center">
          <div>
            <div className="mb-3 inline-flex rounded-full bg-gold-400/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-gold-300">Competitive Research Workspace</div>
            <h1 className="text-3xl font-bold md:text-5xl">Discovery Workbench</h1>
            <p className="mt-4 max-w-3xl text-base leading-7 text-forest-100 md:text-lg">
              Move from public molecular identifiers to a traceable compound/protein library, screening manifest, interaction network and exportable reproducibility record in one workspace.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5 text-sm leading-6 text-forest-100">
            <div className="font-semibold text-gold-300">Compute boundary</div>
            <p className="mt-2">NigerFlora manages research inputs and reproducible job manifests on Vercel. Native AutoDock Vina or molecular-dynamics execution belongs on a dedicated compute worker.</p>
          </div>
        </div>
      </section>

      {error && <PageError message={error} />}
      {notice && <div className="rounded-xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">{notice}</div>}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-forest-800">PubChem Compound Finder</h2>
              <p className="mt-1 text-sm text-gray-500">Search by compound name or PubChem CID and save verified identifiers for downstream work.</p>
            </div>
            <span className="text-3xl">🧪</span>
          </div>
          <div className="mt-5 flex gap-2">
            <input className="input" value={compoundQuery} onChange={(e) => setCompoundQuery(e.target.value)} placeholder="e.g. quercetin or 5280343" />
            <button className="btn-primary whitespace-nowrap" onClick={() => void lookup("compound")} disabled={busy === "compound"}>{busy === "compound" ? <Spinner /> : "Search"}</button>
          </div>
          {compoundResult && (
            <div className="mt-5 grid gap-4 rounded-2xl border border-gray-200 p-4 sm:grid-cols-[140px_1fr]">
              {compoundResult.image_url && <img src={compoundResult.image_url} alt={compoundResult.name} className="h-36 w-36 rounded-xl border bg-white object-contain" />}
              <div className="min-w-0 text-sm">
                <div className="font-bold text-forest-800">{compoundResult.name}</div>
                <div className="mt-1 text-gray-500">CID {compoundResult.external_id} · {compoundResult.molecular_formula} · MW {compoundResult.molecular_weight}</div>
                {compoundResult.canonical_smiles && <div className="mt-2 break-all rounded-lg bg-gray-50 p-2 text-xs text-gray-600">{compoundResult.canonical_smiles}</div>}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="btn-primary" onClick={() => void saveAsset(compoundResult)} disabled={busy === "save-compound"}>Save compound</button>
                  {compoundResult.source_url && <a href={compoundResult.source_url} target="_blank" rel="noreferrer" className="btn-outline">Open PubChem</a>}
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-forest-800">RCSB Protein Structure Finder</h2>
              <p className="mt-1 text-sm text-gray-500">Resolve a PDB structure and preserve its experimental metadata before screening design.</p>
            </div>
            <span className="text-3xl">🧬</span>
          </div>
          <div className="mt-5 flex gap-2">
            <input className="input uppercase" value={proteinQuery} onChange={(e) => setProteinQuery(e.target.value.toUpperCase())} placeholder="e.g. 1IEP" maxLength={4} />
            <button className="btn-primary whitespace-nowrap" onClick={() => void lookup("protein")} disabled={busy === "protein"}>{busy === "protein" ? <Spinner /> : "Search"}</button>
          </div>
          {proteinResult && (
            <div className="mt-5 rounded-2xl border border-gray-200 p-4 text-sm">
              <div className="font-bold text-forest-800">{proteinResult.external_id} · {proteinResult.name}</div>
              <div className="mt-2 grid gap-2 sm:grid-cols-3">
                <div className="rounded-lg bg-gray-50 p-3"><div className="text-xs text-gray-400">Method</div><div className="font-medium">{proteinResult.experimental_method ?? "—"}</div></div>
                <div className="rounded-lg bg-gray-50 p-3"><div className="text-xs text-gray-400">Resolution</div><div className="font-medium">{proteinResult.resolution_angstrom ? `${proteinResult.resolution_angstrom} Å` : "—"}</div></div>
                <div className="rounded-lg bg-gray-50 p-3"><div className="text-xs text-gray-400">Polymer entities</div><div className="font-medium">{proteinResult.polymer_entity_count ?? "—"}</div></div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="btn-primary" onClick={() => void saveAsset(proteinResult)} disabled={busy === "save-protein"}>Save protein</button>
                {proteinResult.source_url && <a href={proteinResult.source_url} target="_blank" rel="noreferrer" className="btn-outline">Open RCSB PDB</a>}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-forest-800">Compound & Protein Library</h2>
            <p className="mt-1 text-sm text-gray-500">Persistent source-linked assets for reproducible project setup.</p>
          </div>
          <button className="btn-outline" onClick={() => void loadWorkspace()} disabled={busy === "load"}>{busy === "load" ? <Spinner /> : "Refresh"}</button>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {assets.map((asset) => (
            <div key={`${asset.kind}-${asset.external_id}`} className="rounded-xl border border-gray-200 p-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">{asset.kind}</span>
                <span className="rounded-full bg-forest-50 px-2 py-1 text-xs text-forest-700">{asset.external_id}</span>
              </div>
              <div className="mt-2 font-semibold text-gray-800">{asset.name}</div>
              <div className="mt-1 text-xs text-gray-500">Source: {asset.source ?? "public database"}</div>
            </div>
          ))}
          {!assets.length && <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 md:col-span-2 xl:col-span-3">Search PubChem and RCSB PDB above, then save assets here.</div>}
        </div>
      </section>

      <section className="card">
        <div className="grid gap-8 xl:grid-cols-[1fr_1.1fr]">
          <div>
            <h2 className="text-xl font-bold text-forest-800">Virtual Screening Manifest</h2>
            <p className="mt-1 text-sm text-gray-500">Build a worker-ready AutoDock Vina-compatible batch job with explicit search-box and reproducibility parameters.</p>

            <div className="mt-5 space-y-4">
              <div>
                <label className="label">Project title</label>
                <input className="input" value={screening.title} onChange={(e) => setScreening((value) => ({ ...value, title: e.target.value }))} placeholder="Quercetin panel against target structure" />
              </div>
              <div>
                <label className="label">Saved receptor</label>
                <select className="input" value={screening.receptor_id} onChange={(e) => setScreening((value) => ({ ...value, receptor_id: e.target.value }))}>
                  <option value="">Select RCSB PDB structure</option>
                  {proteins.map((protein) => <option key={protein.external_id} value={protein.external_id}>{protein.external_id} · {protein.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Saved compounds</label>
                <div className="max-h-52 space-y-2 overflow-y-auto rounded-xl border border-gray-200 p-3">
                  {compounds.map((compound) => (
                    <label key={compound.external_id} className="flex cursor-pointer items-start gap-3 rounded-lg p-2 hover:bg-gray-50">
                      <input type="checkbox" className="mt-1" checked={screening.ligand_ids.includes(compound.external_id)} onChange={() => toggleLigand(compound.external_id)} />
                      <span><span className="font-medium text-gray-800">{compound.name}</span><span className="ml-2 text-xs text-gray-400">CID {compound.external_id}</span></span>
                    </label>
                  ))}
                  {!compounds.length && <div className="text-sm text-gray-500">Save at least one PubChem compound first.</div>}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {(["center_x", "center_y", "center_z"] as const).map((key) => <div key={key}><label className="label">{key.replace("_", " ")}</label><input className="input" value={screening[key]} onChange={(e) => setScreening((value) => ({ ...value, [key]: e.target.value }))} /></div>)}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {(["size_x", "size_y", "size_z"] as const).map((key) => <div key={key}><label className="label">{key.replace("_", " ")}</label><input className="input" value={screening[key]} onChange={(e) => setScreening((value) => ({ ...value, [key]: e.target.value }))} /></div>)}
              </div>
              <div className="grid grid-cols-3 gap-3">
                {(["exhaustiveness", "num_modes", "seed"] as const).map((key) => <div key={key}><label className="label">{key.replace("_", " ")}</label><input className="input" value={screening[key]} onChange={(e) => setScreening((value) => ({ ...value, [key]: e.target.value }))} /></div>)}
              </div>
              <button className="btn-primary w-full" onClick={() => void createScreeningJob()} disabled={busy === "screening"}>{busy === "screening" ? <><Spinner /> Creating manifest…</> : "Create screening manifest"}</button>
            </div>
          </div>

          <div>
            <h3 className="font-bold text-gray-800">Reproducibility history</h3>
            <div className="mt-4 space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="rounded-xl border border-gray-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-gray-800">{job.title}</div>
                      <div className="mt-1 text-xs text-gray-500">{job.id} · receptor {job.manifest.receptor.pdb_id} · {job.manifest.ligands.length} ligand(s)</div>
                    </div>
                    <StatusBadge status={job.status} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
                    <span className="rounded-full bg-gray-100 px-2 py-1">{job.manifest.engine}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-1">exhaustiveness {job.manifest.parameters.exhaustiveness}</span>
                    <span className="rounded-full bg-gray-100 px-2 py-1">modes {job.manifest.parameters.num_modes}</span>
                  </div>
                  <button className="btn-outline mt-3" onClick={() => downloadJson(`${job.id}-manifest.json`, job.manifest)}>Download JSON manifest</button>
                </div>
              ))}
              {!jobs.length && <div className="rounded-xl border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">No screening manifests yet.</div>}
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="grid gap-8 xl:grid-cols-[0.85fr_1.15fr]">
          <div>
            <h2 className="text-xl font-bold text-forest-800">Interaction Network Evidence</h2>
            <p className="mt-1 text-sm text-gray-500">Create Cytoscape-style node/edge evidence without claiming that an association proves biological synergy.</p>
            <div className="mt-5 space-y-4">
              <div><label className="label">Network title</label><input className="input" value={networkTitle} onChange={(e) => setNetworkTitle(e.target.value)} /></div>
              <div>
                <label className="label">Nodes — one per line: id | label | type</label>
                <textarea className="input min-h-32 font-mono text-xs" value={nodesText} onChange={(e) => setNodesText(e.target.value)} />
              </div>
              <div>
                <label className="label">Edges — source | target | relation | evidence</label>
                <textarea className="input min-h-32 font-mono text-xs" value={edgesText} onChange={(e) => setEdgesText(e.target.value)} />
              </div>
              <button className="btn-primary w-full" onClick={() => void saveNetwork()} disabled={busy === "network"}>{busy === "network" ? <><Spinner /> Saving…</> : "Save evidence network"}</button>
            </div>
          </div>
          <div>
            <NetworkPreview nodes={parsedNetwork.nodes} edges={parsedNetwork.edges} />
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">
              Network edges are evidence statements. Preserve the database, DOI, assay, dataset or computational method supporting each edge before using the network in a thesis, article or grant.
            </div>
            <div className="mt-4 space-y-2">
              {networks.slice(0, 5).map((network) => (
                <div key={network.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 px-3 py-2 text-sm">
                  <div><span className="font-medium text-gray-800">{network.title}</span><span className="ml-2 text-xs text-gray-400">{network.nodes.length} nodes · {network.edges.length} edges</span></div>
                  <button className="text-xs font-semibold text-forest-700 hover:underline" onClick={() => downloadJson(`${network.id}.json`, network)}>Export</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-forest-200 bg-forest-50 p-5 text-sm leading-6 text-forest-900">
        <strong>Research integrity:</strong> PubChem and RCSB PDB metadata support identity and provenance. Docking manifests, interaction networks and computational predictions remain hypothesis-generating until validated with appropriate methods and experiments.
      </section>
    </div>
  );
}
