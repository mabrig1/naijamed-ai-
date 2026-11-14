import { useState } from "react";
import axios from "axios";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";

type Asset = {
  kind: "compound" | "protein";
  external_id: string;
  name: string;
  source: string;
  source_url: string;
  image_url?: string;
  molecular_formula?: string;
  molecular_weight?: number;
  connectivity_smiles?: string;
  smiles?: string;
  inchikey?: string;
  experimental_method?: string;
  resolution_angstrom?: number;
  citation_title?: string;
  polymer_entity_count?: number;
};
type LookupResponse = { result: Asset; scientific_notice: string };

function errorDescription(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.response?.status === 502 || error.response?.status === 503) {
      return "The scientific reference provider is temporarily unavailable. Retry shortly.";
    }
  }
  return "The lookup did not complete. Check your connection or try another public identifier.";
}
function exportJson(data: unknown) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const node = document.createElement("a");
  node.href = url;
  node.download = "nigerflora-scientific-reference.json";
  node.click();
  URL.revokeObjectURL(url);
}

export default function ScienceExplorer() {
  const [compoundQuery, setCompoundQuery] = useState("aspirin");
  const [proteinQuery, setProteinQuery] = useState("1CRN");
  const [compound, setCompound] = useState<LookupResponse | null>(null);
  const [protein, setProtein] = useState<LookupResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"compound" | "protein" | "">("");

  async function lookup(kind: "compound" | "protein") {
    const query = (kind === "compound" ? compoundQuery : proteinQuery).trim();
    if (!query || query.length > 80) {
      setError("Enter a compound name, CID or 4-character PDB ID (maximum 80 characters).");
      return;
    }
    setError("");
    setBusy(kind);
    if (kind === "compound") setCompound(null);
    else setProtein(null);
    try {
      // Use bare axios: public scientific lookup must not trigger the private
      // session interceptor or navigate visitors to the login page.
      const response = await axios.post<LookupResponse>("/api/discovery", {
        action: kind === "compound" ? "lookup_compound" : "lookup_protein",
        query,
      }, {
        baseURL: api.defaults.baseURL,
        timeout: 30000,
        headers: { "Content-Type": "application/json", Accept: "application/json" },
      });
      if (!response.data?.result?.external_id || !response.data?.result?.source_url) {
        throw new Error("Invalid scientific reference");
      }
      if (kind === "compound") setCompound(response.data);
      else setProtein(response.data);
    } catch (e) {
      setError(errorDescription(e));
    } finally {
      setBusy("");
    }
  }

  function reference(data: LookupResponse) {
    return {
      ...data.result,
      exported_at: new Date().toISOString(),
      scientific_notice: data.scientific_notice,
      source_note: "Public scientific reference, not an original experiment or clinical result",
    };
  }

  return (
    <main className="min-h-screen bg-cream text-gray-900">
      <header className="bg-forest-900 px-5 py-6 text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
          <Link className="font-bold text-gold-300" to="/">🌿 NigerFlora BioSciences</Link>
          <div className="flex items-center gap-4 text-sm">
            <Link to="/bioinformatics-services" className="hover:underline">Research services</Link>
            <Link to="/login" className="hover:underline">Researcher login</Link>
          </div>
        </div>
      </header>
      <section className="bg-forest-800 px-6 py-12 text-white">
        <div className="mx-auto max-w-6xl">
          <span className="text-sm font-semibold uppercase tracking-wider text-gold-300">Live public scientific references</span>
          <h1 className="mt-3 text-3xl font-bold md:text-5xl">Explore compounds and protein structures</h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-forest-100 md:text-base">
            Look up real records from PubChem and the RCSB Protein Data Bank. View identifiers,
            molecular details, experimental structural evidence, and download a provenance-linked JSON record.
            No account or payment is required.
          </p>
        </div>
      </section>
      <div className="mx-auto max-w-6xl space-y-8 px-5 py-10">
        {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
        <div className="grid gap-6 lg:grid-cols-2">
          <section className="card">
            <h2 className="text-xl font-bold text-forest-800">PubChem compound lookup</h2>
            <p className="mt-2 text-sm text-gray-600">Enter a public compound name or numeric PubChem CID.</p>
            <form className="mt-5 flex gap-3" onSubmit={e => { e.preventDefault(); void lookup("compound"); }}>
              <input aria-label="Compound name or CID" className="input flex-1" maxLength={80} value={compoundQuery}
                onChange={e => setCompoundQuery(e.target.value)} placeholder="e.g. aspirin or 2244" />
              <button type="submit" className="btn-primary" disabled={busy !== ""}>
                {busy === "compound" ? "Searching…" : "Search"}
              </button>
            </form>
            {compound && (
              <article className="mt-6 space-y-3 rounded-xl border border-forest-100 p-4">
                <h3 className="text-lg font-bold">{compound.result.name}</h3>
                {compound.result.image_url && <img className="h-40 max-w-full rounded-lg border bg-white object-contain"
                  src={compound.result.image_url} alt={"2D chemical structure for " + compound.result.name} />}
                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                  <div><dt className="font-semibold">PubChem CID</dt><dd>{compound.result.external_id}</dd></div>
                  <div><dt className="font-semibold">Molecular formula</dt><dd>{compound.result.molecular_formula || "Not reported"}</dd></div>
                  <div><dt className="font-semibold">Molecular weight</dt><dd>{compound.result.molecular_weight ?? "Not reported"}</dd></div>
                  <div className="break-words"><dt className="font-semibold">InChIKey</dt><dd>{compound.result.inchikey || "Not reported"}</dd></div>
                </dl>
                <div className="break-all text-xs"><strong>SMILES: </strong>{compound.result.connectivity_smiles || compound.result.smiles || "Not supplied"}</div>
                <div className="flex flex-wrap gap-3">
                  <a className="text-sm font-semibold text-forest-700 underline" href={compound.result.source_url} target="_blank" rel="noreferrer">View PubChem source</a>
                  <button type="button" className="btn-secondary" onClick={() => exportJson(reference(compound))}>Export JSON</button>
                </div>
              </article>
            )}
          </section>
          <section className="card">
            <h2 className="text-xl font-bold text-forest-800">RCSB protein structure lookup</h2>
            <p className="mt-2 text-sm text-gray-600">Enter a four-character PDB identifier, such as 1CRN or 4HHB.</p>
            <form className="mt-5 flex gap-3" onSubmit={e => { e.preventDefault(); void lookup("protein"); }}>
              <input aria-label="Protein PDB ID" className="input flex-1 uppercase" maxLength={4}
                value={proteinQuery} onChange={e => setProteinQuery(e.target.value.toUpperCase())}
                placeholder="e.g. 1CRN" />
              <button type="submit" className="btn-primary" disabled={busy !== ""}>
                {busy === "protein" ? "Searching…" : "Search"}
              </button>
            </form>
            {protein && (
              <article className="mt-6 space-y-3 rounded-xl border border-forest-100 p-4 text-sm">
                <h3 className="text-lg font-bold">{protein.result.name}</h3>
                <dl className="grid gap-2 sm:grid-cols-2">
                  <div><dt className="font-semibold">PDB ID</dt><dd>{protein.result.external_id}</dd></div>
                  <div><dt className="font-semibold">Experimental method</dt><dd>{protein.result.experimental_method || "Not specified"}</dd></div>
                  <div><dt className="font-semibold">Resolution</dt><dd>{protein.result.resolution_angstrom ? protein.result.resolution_angstrom + " Å" : "Not specified"}</dd></div>
                  <div><dt className="font-semibold">Polymer entities</dt><dd>{protein.result.polymer_entity_count ?? "Not specified"}</dd></div>
                </dl>
                {protein.result.citation_title && <p><strong>Primary citation: </strong>{protein.result.citation_title}</p>}
                <div className="flex flex-wrap gap-3">
                  <a className="font-semibold text-forest-700 underline" href={protein.result.source_url} target="_blank" rel="noreferrer">View RCSB PDB source</a>
                  <button type="button" className="btn-secondary" onClick={() => exportJson(reference(protein))}>Export JSON</button>
                </div>
              </article>
            )}
          </section>
        </div>
        <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-forest-900">
          <strong>Research integrity.</strong> These are external public records, not computed docking energies,
          ADMET measurements, proof of compound efficacy, clinical diagnoses or a drug safety assessment.
          Experimental structures and database properties require interpretation in their original source context.
        </section>
        <div className="flex flex-wrap gap-3">
          <Link className="btn-primary" to="/register">Create account for saved research workspaces</Link>
          <Link className="btn-secondary" to="/research-studio">Explore Research Studio</Link>
        </div>
      </div>
    </main>
  );
}
