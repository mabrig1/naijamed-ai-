import { useState } from "react";

const requirements: Record<string, string[]> = {
  "Network pharmacology": [
    "Document compound and target identifiers and database versions",
    "Record confidence thresholds and network construction settings",
    "Report enrichment background and multiple-testing correction",
    "Archive source tables and scripts"
  ],
  "ADMET screening": [
    "Record canonical compound identifiers and prediction model versions",
    "Report units, thresholds and applicability domains",
    "Document missing data and uncertainty",
    "Archive unmodified prediction outputs"
  ],
  "Molecular docking": [
    "Record protein structures and ligand preparation steps",
    "Record docking engine, grid coordinates and search parameters",
    "Document controls, validation and scoring limitations",
    "Archive input structures, poses and output logs"
  ]
};

export default function MethodsChecklist() {
  const [method, setMethod] = useState("Network pharmacology");
  const [project, setProject] = useState("");
  const [notes, setNotes] = useState("");
  const [done, setDone] = useState<Record<string, boolean>>({});
  const items = requirements[method];
  const checked = items.filter(item => done[method + item]).length;

  function download() {
    const record = {
      schema_version: 1,
      project_title: project,
      method,
      created_at: new Date().toISOString(),
      requirements: items.map(item => ({ description: item, self_reported_complete: !!done[method + item] })),
      notes,
      notice: "Self-reported research documentation only; no independent verification or clinical efficacy established."
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(record, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "nigerflora-methods.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <section className="card space-y-4">
    <h2 className="text-2xl font-bold text-forest-800">Research methods record</h2>
    <p className="text-sm text-gray-600">Document reproducibility requirements before reporting computational findings. Entries remain in your browser until exported.</p>
    <label className="block text-sm font-medium">Project title
      <input className="input mt-1" value={project} maxLength={240} onChange={e => setProject(e.target.value)} />
    </label>
    <label className="block text-sm font-medium">Analysis type
      <select className="input mt-1" value={method} onChange={e => setMethod(e.target.value)}>
        {Object.keys(requirements).map(name => <option key={name}>{name}</option>)}
      </select>
    </label>
    <p role="status" className="text-sm">{checked} of {items.length} requirements marked complete</p>
    {items.map(item => <label key={item} className="flex items-start gap-3 rounded-lg border p-3 text-sm">
      <input type="checkbox" checked={!!done[method + item]} onChange={e => setDone(prev => ({ ...prev, [method + item]: e.target.checked }))} />
      <span>{item}</span>
    </label>)}
    <label className="block text-sm font-medium">Methods and limitations (do not include patient information)
      <textarea className="input mt-1 min-h-24" value={notes} maxLength={10000} onChange={e => setNotes(e.target.value)} />
    </label>
    <button type="button" className="btn-primary" onClick={download}>Export methods record (JSON)</button>
    <p className="text-xs text-gray-500">This checklist does not perform docking, ADMET prediction or clinical validation.</p>
  </section>;
}
