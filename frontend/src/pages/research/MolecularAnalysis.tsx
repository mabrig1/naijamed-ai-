import { useState } from "react";
import { api } from "../../lib/api";

type Molecule = {
  index: number;
  input_smiles: string;
  valid: boolean;
  error?: string;
  canonical_smiles?: string;
  molecular_formula?: string;
  molecular_weight?: number;
  logp?: number;
  tpsa?: number;
  h_bond_donors?: number;
  h_bond_acceptors?: number;
};

export default function MolecularAnalysis() {
  const [input, setInput] = useState("CCO\nO=C=O");
  const [results, setResults] = useState<Molecule[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function analyze() {
    const smiles = input.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    if (!smiles.length || smiles.length > 20 || smiles.some(value => value.length > 2048)) {
      setError("Enter between 1 and 20 SMILES structures, each at most 2,048 characters.");
      setResults([]);
      return;
    }
    setBusy(true);
    setError("");
    setResults([]);
    try {
      const response = await api.post<{ results: Molecule[] }>("/api/research/molecules/analyze", { smiles });
      setResults(response.data.results);
    } catch (reason: unknown) {
      const detail = (reason as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || "Molecular analysis is unavailable. Sign in and check that the research service is configured.");
    } finally {
      setBusy(false);
    }
  }

  function exportResults() {
    const data = { exported_at: new Date().toISOString(), results, notice: "Research-only descriptors, not ADMET or clinical safety predictions." };
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "nigerflora-molecular-descriptors.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="card space-y-4" aria-labelledby="molecular-analysis-title">
    <h2 id="molecular-analysis-title" className="text-2xl font-bold text-forest-800">Molecular structure analysis</h2>
    <p className="text-sm text-gray-600">Enter one SMILES string per line (maximum 20). The authenticated research API calculates basic molecular descriptors when RDKit is configured.</p>
    <label className="block text-sm font-medium">SMILES structures
      <textarea className="input mt-1 min-h-28 font-mono text-sm" value={input} onChange={event => setInput(event.target.value)} maxLength={42000} />
    </label>
    <button type="button" className="btn-primary" disabled={busy} onClick={() => void analyze()}>{busy ? "Analyzing…" : "Analyze structures"}</button>
    {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
    {results.length > 0 && <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] text-left text-sm">
          <thead><tr className="border-b"><th className="p-2">Input</th><th className="p-2">Canonical SMILES</th><th className="p-2">Formula</th><th className="p-2">MW</th><th className="p-2">LogP</th><th className="p-2">TPSA</th><th className="p-2">HBD/HBA</th></tr></thead>
          <tbody>{results.map(item => <tr key={item.index} className="border-b">
            <td className="max-w-40 break-all p-2 font-mono">{item.input_smiles}</td>
            {item.valid ? <>
              <td className="max-w-48 break-all p-2 font-mono">{item.canonical_smiles}</td>
              <td className="p-2">{item.molecular_formula}</td>
              <td className="p-2">{item.molecular_weight}</td>
              <td className="p-2">{item.logp}</td>
              <td className="p-2">{item.tpsa}</td>
              <td className="p-2">{item.h_bond_donors}/{item.h_bond_acceptors}</td>
            </> : <td className="p-2 text-red-700" colSpan={6}>{item.error || "Invalid structure"}</td>}
          </tr>)}</tbody>
        </table>
      </div>
      <button type="button" className="btn-primary" onClick={exportResults}>Export results (JSON)</button>
    </>}
    <p className="text-xs text-gray-500">Research use only. Descriptors do not establish ADMET, toxicity, binding affinity, efficacy or clinical safety.</p>
  </section>;
}
