import { useMemo, useState } from "react";

type Compound = { identifier: string; smiles: string; source: string };
type Finding = { row: number; issue: string };
const MAX_ROWS = 1000;
const MAX_BYTES = 250000;

function parseCsv(input: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], cell = "", quoted = false;
  for (let i = 0; i < input.length; i++) {
    const char = input[i];
    if (char === '"') {
      if (quoted && input[i + 1] === '"') { cell += '"'; i++; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell); cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && input[i + 1] === "\n") i++;
      row.push(cell); cell = "";
      if (row.some(value => value.trim())) rows.push(row);
      row = [];
    } else cell += char;
  }
  if (quoted) throw new Error("CSV contains an unclosed quoted field.");
  row.push(cell);
  if (row.some(value => value.trim())) rows.push(row);
  return rows;
}

function inspect(input: string): { compounds: Compound[]; findings: Finding[] } {
  const rows = parseCsv(input);
  if (!rows.length) return { compounds: [], findings: [] };
  const header = rows[0].map(value => value.trim().toLowerCase());
  const columns = ["identifier", "smiles", "source"].map(name => header.indexOf(name));
  if (columns.some(index => index < 0)) throw new Error("Required CSV headers: identifier,smiles,source");
  if (rows.length - 1 > MAX_ROWS) throw new Error("Maximum 1,000 compound rows.");
  const compounds: Compound[] = [];
  const findings: Finding[] = [];
  const seen = new Set<string>();
  rows.slice(1).forEach((values, index) => {
    const row = index + 2;
    if (values.length !== header.length) findings.push({ row, issue: "Unexpected number of CSV columns" });
    const [identifier, smiles, source] = columns.map(column => (values[column] || "").trim());
    if (!identifier || !smiles || !source) findings.push({ row, issue: "Missing identifier, SMILES or source" });
    if (identifier && seen.has(identifier.toLowerCase())) findings.push({ row, issue: "Duplicate compound identifier" });
    if (identifier) seen.add(identifier.toLowerCase());
    if (smiles && /\s/.test(smiles)) findings.push({ row, issue: "SMILES contains whitespace; review structure" });
    compounds.push({ identifier, smiles, source });
  });
  return { compounds, findings };
}

export default function CompoundDatasetValidator() {
  const [input, setInput] = useState("identifier,smiles,source\n");
  const [filename, setFilename] = useState("manual-entry.csv");
  const [error, setError] = useState("");
  const result = useMemo(() => {
    try { return inspect(input); } catch (reason) { return { compounds: [], findings: [], parseError: String(reason) }; }
  }, [input]);

  async function upload(file?: File) {
    if (!file) return;
    if (file.size > MAX_BYTES) { setError("File exceeds 250 KB."); return; }
    setError("");
    setFilename(file.name);
    setInput(await file.text());
  }

  function exportReport() {
    const report = {
      schema_version: 1,
      filename,
      inspected_at: new Date().toISOString(),
      row_count: result.compounds.length,
      findings: result.findings,
      compounds: result.compounds,
      warning: "Format and completeness checks only. SMILES chemical validity, stereochemistry and toxicity are not verified."
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "nigerflora-compound-audit.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const parseError = "parseError" in result ? String(result.parseError) : "";
  return <section className="card space-y-4" aria-labelledby="dataset-title">
    <h2 id="dataset-title" className="text-2xl font-bold text-forest-800">Compound dataset intake</h2>
    <p className="text-sm text-gray-600">Upload a CSV containing identifier, smiles and source columns. Validation runs locally in your browser; data is not uploaded to the server.</p>
    <input aria-label="Upload compound CSV" type="file" accept=".csv,text/csv" onChange={event => void upload(event.target.files?.[0])} />
    <label className="block text-sm font-medium">CSV dataset
      <textarea className="input mt-1 min-h-36 font-mono text-xs" maxLength={MAX_BYTES} value={input} onChange={event => setInput(event.target.value)} />
    </label>
    {(error || parseError) && <p role="alert" className="text-sm text-red-700">{error || parseError}</p>}
    {!parseError && <p role="status" className="text-sm">{result.compounds.length} compounds · {result.findings.length} findings</p>}
    {result.findings.length > 0 && <ul className="max-h-48 space-y-1 overflow-y-auto text-sm text-amber-800">
      {result.findings.slice(0, 30).map((finding, index) => <li key={index}>Row {finding.row}: {finding.issue}</li>)}
    </ul>}
    <button className="btn-primary" type="button" disabled={!!parseError || !!error} onClick={exportReport}>Export dataset audit (JSON)</button>
    <p className="text-xs text-gray-500">This tool does not verify chemical structures or perform ADMET predictions, docking or therapeutic assessment. Use cheminformatics software and expert review before downstream analysis.</p>
  </section>;
}
