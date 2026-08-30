import { useEffect, useMemo, useState } from "react";
import { api } from "../../lib/api";
import { Spinner } from "../../components/Layout";

interface ResearchService {
  id: string;
  category: string;
  name: string;
  description: string;
  price_kobo: number;
  price_label: string;
  deliverables: string[];
}

interface SynergyFramework {
  name: string;
  status: string;
  purpose: string;
  stages: string[];
  guardrail: string;
}

interface CatalogResponse {
  studio: string;
  services: ResearchService[];
  synergy_framework: SynergyFramework;
  integrity_notice: string;
}

const CATEGORY_ORDER = [
  "Bioinformatics Consulting",
  "Research Production",
  "Grant & Proposal Consulting",
  "Training & Digital Products",
];

export default function ResearchStudio() {
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ResearchService | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [orderForm, setOrderForm] = useState({ project_title: "", institution: "", notes: "" });
  const [plants, setPlants] = useState("");
  const [indication, setIndication] = useState("");
  const [targets, setTargets] = useState("");
  const [synergyMessage, setSynergyMessage] = useState("");
  const [synergyLoading, setSynergyLoading] = useState(false);

  useEffect(() => {
    api.get<CatalogResponse>("/api/research-studio")
      .then(({ data }) => setCatalog(data))
      .catch((err: unknown) => {
        const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        setError(message ?? "Could not load the Research Studio catalog.");
      })
      .finally(() => setLoading(false));
  }, []);

  const grouped = useMemo(() => {
    const result = new Map<string, ResearchService[]>();
    for (const service of catalog?.services ?? []) {
      const rows = result.get(service.category) ?? [];
      rows.push(service);
      result.set(service.category, rows);
    }
    return result;
  }, [catalog]);

  async function startCheckout() {
    if (!selected) return;
    setCheckoutLoading(true);
    setError("");
    try {
      const { data } = await api.post<{ authorization_url: string }>("/api/research-studio", {
        action: "create_order",
        service_id: selected.id,
        project_title: orderForm.project_title || undefined,
        institution: orderForm.institution || undefined,
        notes: orderForm.notes || undefined,
        callback_url: `${window.location.origin}/research-studio?payment=return`,
      });
      if (data.authorization_url) window.location.assign(data.authorization_url);
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(message ?? "Unable to start checkout.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function createSynergyProject() {
    const plantList = plants.split(",").map((item) => item.trim()).filter(Boolean);
    const targetList = targets.split(",").map((item) => item.trim()).filter(Boolean);
    if (plantList.length < 2) {
      setSynergyMessage("Enter at least two plants, separated by commas.");
      return;
    }
    setSynergyLoading(true);
    setSynergyMessage("");
    try {
      const { data } = await api.post<{ project_id: string }>("/api/research-studio", {
        action: "create_synergy_project",
        project_title: `${indication || "Polyherbal"} computational synergy study`,
        plants: plantList,
        indication: indication || undefined,
        targets: targetList,
      });
      setSynergyMessage(`Project ${data.project_id} created. Begin with compound standardization and dataset curation.`);
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setSynergyMessage(message ?? "Could not create the synergy project.");
    } finally {
      setSynergyLoading(false);
    }
  }

  if (loading) {
    return <div className="flex min-h-[50vh] items-center justify-center"><Spinner /></div>;
  }

  return (
    <div className="space-y-10">
      <section className="overflow-hidden rounded-3xl bg-forest-800 text-white shadow-xl">
        <div className="grid gap-8 px-6 py-10 md:grid-cols-[1.35fr_0.65fr] md:px-10 md:py-14">
          <div>
            <div className="mb-3 inline-flex rounded-full bg-gold-300/15 px-3 py-1 text-xs font-semibold text-gold-300">
              Mabrig HealthOS · Research & Discovery Studio
            </div>
            <h1 className="max-w-3xl text-3xl font-bold leading-tight md:text-5xl">
              Turn computational research expertise into premium digital services.
            </h1>
            <p className="mt-5 max-w-2xl text-sm leading-7 text-forest-100 md:text-base">
              Order network pharmacology, ADMET screening, molecular docking support, scientific visualization,
              grant architecture and practical in-silico research training from one workflow.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 text-xs text-forest-100">
              {['M.Sc. & Ph.D. research', 'Academic departments', 'Herbal discovery teams', 'Grant applicants'].map((item) => (
                <span key={item} className="rounded-full border border-forest-500 px-3 py-1.5">{item}</span>
              ))}
            </div>
          </div>
          <div className="rounded-2xl bg-white/10 p-6 backdrop-blur-sm">
            <div className="text-sm font-semibold text-gold-300">Research integrity first</div>
            <p className="mt-3 text-sm leading-6 text-forest-100">
              Computational outputs are research evidence, not clinical proof. Every service keeps methods,
              parameters and researcher responsibility visible so results remain reproducible and defensible.
            </p>
          </div>
        </div>
      </section>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">⚠️ {error}</div>
      )}

      <section className="space-y-8">
        {CATEGORY_ORDER.map((category) => {
          const services = grouped.get(category) ?? [];
          if (services.length === 0) return null;
          return (
            <div key={category}>
              <div className="mb-4 flex items-end justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-bold text-forest-800">{category}</h2>
                  <p className="mt-1 text-sm text-gray-500">Defined deliverables, transparent starting prices and project tracking.</p>
                </div>
              </div>
              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {services.map((service) => (
                  <article key={service.id} className="card flex h-full flex-col border border-forest-100 shadow-sm">
                    <div className="text-xs font-semibold uppercase tracking-wide text-forest-500">{service.category}</div>
                    <h3 className="mt-2 text-xl font-bold text-gray-900">{service.name}</h3>
                    <p className="mt-3 flex-1 text-sm leading-6 text-gray-600">{service.description}</p>
                    <ul className="mt-4 space-y-1.5 text-sm text-gray-600">
                      {service.deliverables.slice(0, 4).map((item) => <li key={item}>✓ {item}</li>)}
                    </ul>
                    <div className="mt-6 flex items-center justify-between gap-3 border-t border-gray-100 pt-4">
                      <span className="font-bold text-forest-700">{service.price_label}</span>
                      <button className="btn-primary" onClick={() => setSelected(service)}>Request service</button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          );
        })}
      </section>

      {catalog?.synergy_framework && (
        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-3xl bg-gradient-to-br from-forest-800 to-forest-600 p-7 text-white shadow-lg">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-gold-300">Signature research niche</div>
            <h2 className="mt-3 text-3xl font-bold">{catalog.synergy_framework.name}</h2>
            <p className="mt-3 text-sm font-medium text-forest-200">{catalog.synergy_framework.status}</p>
            <p className="mt-5 text-sm leading-7 text-forest-100">{catalog.synergy_framework.purpose}</p>
            <ol className="mt-6 space-y-2 text-sm text-forest-100">
              {catalog.synergy_framework.stages.map((stage, index) => (
                <li key={stage} className="flex gap-3"><span className="font-bold text-gold-300">{index + 1}.</span><span>{stage}</span></li>
              ))}
            </ol>
          </div>

          <div className="card border border-gold-200">
            <h3 className="text-2xl font-bold text-forest-800">Start a Polyherbal Interaction Network project</h3>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              Create a project record for a multi-plant study. The workspace is designed for compound curation,
              target mapping, docking evidence and later wet-lab validation—not automated efficacy claims.
            </p>
            <div className="mt-6 space-y-4">
              <div>
                <label className="label">Plants</label>
                <input className="input" value={plants} onChange={(e) => setPlants(e.target.value)} placeholder="e.g. Vernonia amygdalina, Gongronema latifolium, ..." />
                <p className="mt-1 text-xs text-gray-400">Separate plant names with commas.</p>
              </div>
              <div>
                <label className="label">Research indication</label>
                <input className="input" value={indication} onChange={(e) => setIndication(e.target.value)} placeholder="e.g. metabolic syndrome" />
              </div>
              <div>
                <label className="label">Known targets, optional</label>
                <input className="input" value={targets} onChange={(e) => setTargets(e.target.value)} placeholder="e.g. AKT1, EGFR, TNF" />
              </div>
              <button className="btn-primary flex items-center gap-2" onClick={createSynergyProject} disabled={synergyLoading}>
                {synergyLoading ? <><Spinner /> Creating…</> : "Create PSI-β project"}
              </button>
              {synergyMessage && <div className="rounded-lg bg-forest-50 p-3 text-sm text-forest-700">{synergyMessage}</div>}
              <p className="text-xs leading-5 text-gray-500">{catalog.synergy_framework.guardrail}</p>
            </div>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-forest-100 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold text-forest-800">From in-silico evidence to a regulated product</h2>
        <div className="mt-5 grid gap-3 text-sm md:grid-cols-4">
          {[
            ["1", "Computational evidence", "Network, ADMET and reproducible docking"],
            ["2", "Experimental validation", "In-vitro/in-vivo testing, safety and standardized extracts"],
            ["3", "IP & grant strategy", "Professional patent review and funder-ready evidence package"],
            ["4", "Regulatory pathway", "NAFDAC-facing product development after required evidence"],
          ].map(([step, title, text]) => (
            <div key={step} className="rounded-xl bg-cream p-4">
              <div className="text-sm font-bold text-gold-600">STEP {step}</div>
              <div className="mt-2 font-semibold text-gray-900">{title}</div>
              <p className="mt-2 text-xs leading-5 text-gray-500">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {selected && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/50 p-4" onClick={() => setSelected(null)}>
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wide text-forest-500">Service request</div>
                <h3 className="mt-1 text-2xl font-bold text-gray-900">{selected.name}</h3>
                <div className="mt-1 font-semibold text-forest-700">{selected.price_label}</div>
              </div>
              <button className="text-2xl text-gray-400 hover:text-gray-700" onClick={() => setSelected(null)}>×</button>
            </div>
            <div className="mt-6 space-y-4">
              <div>
                <label className="label">Project title</label>
                <input className="input" value={orderForm.project_title} onChange={(e) => setOrderForm((f) => ({ ...f, project_title: e.target.value }))} placeholder="Your thesis, article or research project" />
              </div>
              <div>
                <label className="label">Institution / Department</label>
                <input className="input" value={orderForm.institution} onChange={(e) => setOrderForm((f) => ({ ...f, institution: e.target.value }))} placeholder="University or research organization" />
              </div>
              <div>
                <label className="label">Project instructions</label>
                <textarea className="input min-h-28" value={orderForm.notes} onChange={(e) => setOrderForm((f) => ({ ...f, notes: e.target.value }))} placeholder="Describe compounds, plants, targets, datasets, deadline and expected outputs." />
              </div>
              <div className="rounded-lg bg-gold-50 p-3 text-xs leading-5 text-gray-600">
                Payment starts the service request. Final scope may be adjusted only with your approval if the dataset or computational workload materially differs from the base package.
              </div>
              <button className="btn-primary flex w-full items-center justify-center gap-2" disabled={checkoutLoading} onClick={startCheckout}>
                {checkoutLoading ? <><Spinner /> Opening secure checkout…</> : `Continue to Paystack · ${selected.price_label}`}
              </button>
            </div>
          </div>
        </div>
      )}

      {catalog?.integrity_notice && (
        <p className="pb-4 text-center text-xs leading-5 text-gray-500">{catalog.integrity_notice}</p>
      )}
    </div>
  );
}
