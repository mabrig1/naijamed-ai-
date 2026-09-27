import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, ProgressBar, Spinner, StatusBadge } from "../components/Layout";
import { useAuth } from "../contexts/AuthContext";

type Account = {
  is_pro: boolean;
  grant_project_count: number;
  grant_project_limit: number | null;
};

type ReadinessCheck = {
  key: string;
  label: string;
  points: number;
  earned: number;
  status: "ready" | "gap";
  note: string;
};

type Readiness = {
  score: number;
  stage: string;
  earned_points: number;
  max_points: number;
  checks: ReadinessCheck[];
  risks: string[];
  budget: {
    project_total: number;
    work_package_total: number;
    unallocated: number | null;
  };
};

type ProjectSummary = {
  id: string;
  title: string;
  acronym?: string | null;
  project_type: string;
  originator_name: string;
  host_institution?: string | null;
  country?: string | null;
  location?: string | null;
  duration_months?: number | null;
  budget_amount?: number | null;
  budget_currency?: string | null;
  funder_name?: string | null;
  call_reference?: string | null;
  call_url?: string | null;
  deadline?: string | null;
  summary?: string | null;
  problem_statement?: string | null;
  objectives: string[];
  confidentiality_level: string;
  status: string;
  readiness?: Readiness;
};

type Related = Record<string, any>;

type ProjectBundle = {
  project: ProjectSummary;
  partners: Related[];
  work_packages: Related[];
  milestones: Related[];
  ip_assets: Related[];
  disclosures: Related[];
  readiness: Readiness;
  watermark: string;
};

type Home = { projects: ProjectSummary[]; account: Account };

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function money(amount?: number | null, currency = "NGN") {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency} ${new Intl.NumberFormat("en-NG").format(amount)}`;
  }
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

const NEXUS_OBJECTIVES = [
  "Establish longitudinal One Health AMR surveillance across human, animal, food and environmental systems.",
  "Characterise genomic transmission pathways and resistance determinants across One Health sectors.",
  "Model climate and environmental drivers of antimicrobial resistance and build predictive risk intelligence.",
  "Develop a translational antimicrobial-discovery pipeline using rigorously selected Nigerian biological resources.",
  "Evaluate stewardship, infection-prevention and implementation interventions and their economic impact.",
  "Build sustainable African research capacity, biobanking, data infrastructure and international partnerships.",
];

export default function FormularyGrantStudio() {
  const { user } = useAuth();
  const [home, setHome] = useState<Home | null>(null);
  const [selected, setSelected] = useState<ProjectBundle | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [project, setProject] = useState({
    title: "",
    acronym: "",
    project_type: "flagship_research",
    originator_name: user?.full_name || "",
    host_institution: "",
    country: "Nigeria",
    location: "",
    duration_months: "60",
    budget_amount: "",
    budget_currency: "NGN",
    funder_name: "",
    call_reference: "",
    call_url: "",
    deadline: "",
    summary: "",
    problem_statement: "",
    objectives: "",
    confidentiality_level: "controlled",
  });

  const [partner, setPartner] = useState({
    organization: "",
    country: "",
    partner_type: "university",
    status: "prospect",
    proposed_role: "",
    lead_contact: "",
    contact_email: "",
  });

  const [workPackage, setWorkPackage] = useState({
    title: "",
    sequence: "1",
    lead_partner: "",
    objective: "",
    outputs: "",
    budget_amount: "",
  });

  const [milestone, setMilestone] = useState({
    title: "",
    milestone_type: "proposal",
    due_on: "",
    status: "planned",
    owner: "",
    evidence: "",
  });

  const [ipAsset, setIpAsset] = useState({
    title: "",
    category: "background_ip",
    ownership_statement: "",
    evidence_reference: "",
    created_before_collaboration: true,
    disclosure_level: "controlled",
  });

  const [disclosure, setDisclosure] = useState({
    recipient_name: "",
    recipient_organization: "",
    disclosed_at: new Date().toISOString().slice(0, 16),
    material: "",
    version: "v1.0",
    purpose: "",
    confidentiality_basis: "",
    notes: "",
  });

  async function loadHome() {
    const { data } = await api.get<Home>("/api/formulary/grants");
    setHome(data);
    return data;
  }

  async function loadProject(id: string) {
    setAction("project");
    setError("");
    try {
      const { data } = await api.get<ProjectBundle>(`/api/formulary/grants/projects/${id}`);
      setSelected(data);
      setWorkPackage((current) => ({
        ...current,
        sequence: String((data.work_packages?.length ?? 0) + 1),
      }));
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  useEffect(() => {
    loadHome()
      .then((data) => data.projects[0] ? loadProject(data.projects[0].id) : undefined)
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadNexusTemplate() {
    setProject((current) => ({
      ...current,
      title: "Climate-Smart One Health Surveillance and Translational Antimicrobial Innovation for Drug-Resistant Infections in Southeast Nigeria",
      acronym: "NEXUS-AMR Africa",
      project_type: "flagship_research",
      originator_name: user?.full_name || current.originator_name,
      host_institution: "University of Nigeria, Nsukka (UNN)",
      country: "Nigeria",
      location: "Nsukka, Enugu State",
      duration_months: "60",
      budget_amount: "1000000000",
      budget_currency: "NGN",
      summary: "A five-year African-led One Health research and innovation programme integrating antimicrobial-resistance surveillance, genomics, climate intelligence, stewardship interventions, health economics and translational antimicrobial discovery, with UNN as the coordinating research hub.",
      problem_statement: "Antimicrobial resistance moves across hospitals, households, livestock, farms, food systems, wastewater and the wider environment, yet these sectors are frequently studied separately. Southeast Nigeria needs an integrated platform capable of characterising transmission, environmental and behavioural drivers, intervention opportunities and new antimicrobial research leads while building durable African research capacity.",
      objectives: NEXUS_OBJECTIVES.join("\n"),
      confidentiality_level: "controlled",
    }));
    setMessage("NEXUS-AMR Africa template loaded. Add a funder/call only after verifying the live opportunity.");
  }

  async function createProject() {
    setAction("create");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<ProjectBundle>("/api/formulary/grants/projects", {
        title: project.title,
        acronym: project.acronym || null,
        project_type: project.project_type,
        originator_name: project.originator_name,
        host_institution: project.host_institution || null,
        country: project.country || null,
        location: project.location || null,
        duration_months: project.duration_months ? Number(project.duration_months) : null,
        budget_amount: project.budget_amount ? Number(project.budget_amount) : null,
        budget_currency: project.budget_currency,
        funder_name: project.funder_name || null,
        call_reference: project.call_reference || null,
        call_url: project.call_url || null,
        deadline: project.deadline ? new Date(project.deadline).toISOString() : null,
        summary: project.summary || null,
        problem_statement: project.problem_statement || null,
        objectives: project.objectives.split("\n").map((value) => value.trim()).filter(Boolean),
        confidentiality_level: project.confidentiality_level,
      });
      setMessage("Grant project created. Record background IP before broader disclosure.");
      await loadHome();
      await loadProject(data.project.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function refreshSelected() {
    if (!selected) return;
    await loadProject(selected.project.id);
    await loadHome();
  }

  async function addRelated(
    kind: "partners" | "work-packages" | "milestones" | "ip-assets" | "disclosures",
    payload: Record<string, unknown>,
  ) {
    if (!selected) return;
    setAction(kind);
    setError("");
    setMessage("");
    try {
      await api.post(`/api/formulary/grants/projects/${selected.project.id}/${kind}`, payload);
      setMessage(`${titleCase(kind.replace(/s$/, ""))} added.`);
      await refreshSelected();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function updateStatus(status: string) {
    if (!selected) return;
    setAction("status");
    setError("");
    try {
      await api.patch(`/api/formulary/grants/projects/${selected.project.id}`, { status });
      setMessage(`Project status updated to ${titleCase(status)}.`);
      await refreshSelected();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  function copyWatermark() {
    if (!selected) return;
    navigator.clipboard.writeText(selected.watermark).then(
      () => setMessage("Controlled-disclosure watermark copied."),
      () => setMessage(selected.watermark),
    );
  }

  if (loading && !home) {
    return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  }

  if (error && !home) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary International Grant Project Studio</div>
            <h1 className="mt-3 text-4xl font-bold">Build the consortium, protect the origin trail, and make the proposal submission-ready.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Manage flagship projects from concept through institutional engagement, partnership, budget architecture, controlled disclosure and grant submission.
            </p>
          </div>
          <div className="min-w-64 rounded-2xl border border-white/10 bg-white/10 p-5 text-sm">
            <div className="text-xs text-forest-200">Projects created</div>
            <div className="mt-1 text-3xl font-bold text-gold-300">{home?.account.grant_project_count ?? 0}</div>
            <div className="mt-2 text-xs text-forest-200">
              {home?.account.is_pro ? "Unlimited with Formulary Scholar" : `Free limit: ${home?.account.grant_project_limit ?? 1}`}
            </div>
            {!home?.account.is_pro && <Link to="/pricing" className="mt-4 block rounded-xl bg-gold-400 px-4 py-2.5 text-center font-bold text-forest-900">Upgrade to Scholar</Link>}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link className="btn-outline" to="/formulary">← Formulary</Link>
        <Link className="btn-outline" to="/formulary/copilot">Regulatory & Grant Copilot</Link>
        <Link className="btn-outline" to="/formulary/portfolio">Research Portfolio</Link>
        <Link className="btn-outline" to="/formulary/journal">Journal Club</Link>
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div className="space-y-6">
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-bold text-forest-800">Create flagship project</h2>
              <button className="btn-outline text-xs" onClick={loadNexusTemplate}>Load NEXUS-AMR template</button>
            </div>
            <div className="mt-4 space-y-3">
              <input className="input" placeholder="Project title" value={project.title} onChange={(e) => setProject((v) => ({ ...v, title: e.target.value }))} />
              <div className="grid gap-3 sm:grid-cols-2">
                <input className="input" placeholder="Acronym" value={project.acronym} onChange={(e) => setProject((v) => ({ ...v, acronym: e.target.value }))} />
                <select className="input" value={project.project_type} onChange={(e) => setProject((v) => ({ ...v, project_type: e.target.value }))}>
                  <option value="flagship_research">Flagship research programme</option>
                  <option value="consortium">International consortium</option>
                  <option value="implementation">Implementation grant</option>
                  <option value="fellowship">Fellowship / investigator award</option>
                  <option value="infrastructure">Research infrastructure</option>
                </select>
              </div>
              <input className="input" placeholder="Concept originator" value={project.originator_name} onChange={(e) => setProject((v) => ({ ...v, originator_name: e.target.value }))} />
              <div className="grid gap-3 sm:grid-cols-2">
                <input className="input" placeholder="Proposed host institution" value={project.host_institution} onChange={(e) => setProject((v) => ({ ...v, host_institution: e.target.value }))} />
                <input className="input" placeholder="Location" value={project.location} onChange={(e) => setProject((v) => ({ ...v, location: e.target.value }))} />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <input className="input" type="number" placeholder="Duration months" value={project.duration_months} onChange={(e) => setProject((v) => ({ ...v, duration_months: e.target.value }))} />
                <input className="input" type="number" placeholder="Total budget" value={project.budget_amount} onChange={(e) => setProject((v) => ({ ...v, budget_amount: e.target.value }))} />
                <input className="input" placeholder="Currency" value={project.budget_currency} onChange={(e) => setProject((v) => ({ ...v, budget_currency: e.target.value.toUpperCase() }))} />
              </div>
              <div className="rounded-2xl bg-cream p-4">
                <div className="text-sm font-semibold text-forest-800">Funding target</div>
                <div className="mt-3 space-y-2">
                  <input className="input" placeholder="Funder name" value={project.funder_name} onChange={(e) => setProject((v) => ({ ...v, funder_name: e.target.value }))} />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input className="input" placeholder="Call reference" value={project.call_reference} onChange={(e) => setProject((v) => ({ ...v, call_reference: e.target.value }))} />
                    <input className="input" placeholder="Official call URL" value={project.call_url} onChange={(e) => setProject((v) => ({ ...v, call_url: e.target.value }))} />
                  </div>
                  <input className="input" type="datetime-local" value={project.deadline} onChange={(e) => setProject((v) => ({ ...v, deadline: e.target.value }))} />
                </div>
              </div>
              <textarea className="input min-h-28" placeholder="Executive summary" value={project.summary} onChange={(e) => setProject((v) => ({ ...v, summary: e.target.value }))} />
              <textarea className="input min-h-28" placeholder="Problem statement and international significance" value={project.problem_statement} onChange={(e) => setProject((v) => ({ ...v, problem_statement: e.target.value }))} />
              <textarea className="input min-h-36" placeholder="Objectives — one per line" value={project.objectives} onChange={(e) => setProject((v) => ({ ...v, objectives: e.target.value }))} />
              <button className="btn-primary w-full" disabled={action === "create" || project.title.length < 3 || project.originator_name.length < 2} onClick={createProject}>
                {action === "create" ? "Creating…" : "Create International Grant Project"}
              </button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-bold text-forest-800">Project portfolio</h2>
            <div className="mt-4 space-y-2">
              {home?.projects.length ? home.projects.map((row) => (
                <button key={row.id} onClick={() => loadProject(row.id)} className={`w-full rounded-xl border p-3 text-left ${selected?.project.id === row.id ? "border-forest-500 bg-forest-50" : "border-gray-100 hover:border-forest-200"}`}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-gray-900">{row.acronym || row.title}</div>
                      <div className="mt-1 text-xs text-gray-500">{row.host_institution || "Host not set"} · {titleCase(row.status)}</div>
                    </div>
                    <span className="rounded-full bg-forest-50 px-2 py-1 text-xs font-bold text-forest-700">{row.readiness?.score ?? 0}%</span>
                  </div>
                </button>
              )) : <p className="text-sm text-gray-400">No international grant project yet.</p>}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {selected ? (
            <>
              <div className="card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wide text-forest-500">{selected.project.acronym || titleCase(selected.project.project_type)}</div>
                    <h2 className="mt-1 text-2xl font-bold text-gray-900">{selected.project.title}</h2>
                    <p className="mt-2 text-sm text-gray-600">{selected.project.host_institution || "Host institution not yet assigned"}{selected.project.location ? ` · ${selected.project.location}` : ""}</p>
                  </div>
                  <StatusBadge status={selected.project.status === "submitted" || selected.project.status === "awarded" ? "completed" : "active"} />
                </div>

                <div className="mt-5 grid gap-3 sm:grid-cols-4">
                  <div className="rounded-xl bg-cream p-3"><div className="text-xs text-gray-500">Budget</div><div className="mt-1 font-bold">{money(selected.project.budget_amount, selected.project.budget_currency || "NGN")}</div></div>
                  <div className="rounded-xl bg-cream p-3"><div className="text-xs text-gray-500">Partners</div><div className="mt-1 font-bold">{selected.partners.length}</div></div>
                  <div className="rounded-xl bg-cream p-3"><div className="text-xs text-gray-500">Work packages</div><div className="mt-1 font-bold">{selected.work_packages.length}</div></div>
                  <div className="rounded-xl bg-cream p-3"><div className="text-xs text-gray-500">Disclosures</div><div className="mt-1 font-bold">{selected.disclosures.length}</div></div>
                </div>

                <div className="mt-5 rounded-2xl border border-gold-200 bg-gold-50 p-4">
                  <div className="text-xs font-bold uppercase tracking-wide text-gold-700">Controlled-disclosure watermark</div>
                  <p className="mt-2 break-words text-xs leading-5 text-gray-700">{selected.watermark}</p>
                  <button className="btn-outline mt-3 text-xs" onClick={copyWatermark}>Copy watermark</button>
                </div>

                <div className="mt-5 flex flex-wrap gap-2">
                  {["concept", "institutional_engagement", "consortium_building", "drafting", "internal_review", "submitted"].map((value) => (
                    <button key={value} disabled={action === "status"} onClick={() => updateStatus(value)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${selected.project.status === value ? "bg-forest-700 text-white" : "bg-gray-100 text-gray-600"}`}>{titleCase(value)}</button>
                  ))}
                </div>
              </div>

              <div className="card">
                <div className="flex items-center justify-between gap-3">
                  <div><h3 className="text-xl font-bold text-forest-800">Grant readiness</h3><p className="mt-1 text-sm text-gray-500">{titleCase(selected.readiness.stage)}</p></div>
                  <div className="text-3xl font-bold text-forest-700">{selected.readiness.score}%</div>
                </div>
                <div className="mt-4"><ProgressBar value={selected.readiness.score} /></div>
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  {selected.readiness.checks.map((check) => (
                    <div key={check.key} className={`rounded-xl border p-3 ${check.status === "ready" ? "border-forest-100 bg-forest-50" : "border-amber-100 bg-amber-50"}`}>
                      <div className="flex items-center justify-between gap-2"><span className="text-sm font-semibold">{check.label}</span><span className="text-xs">{check.earned}/{check.points}</span></div>
                      <p className="mt-2 text-xs leading-5 text-gray-600">{check.note}</p>
                    </div>
                  ))}
                </div>
                {!!selected.readiness.risks.length && (
                  <div className="mt-5 rounded-2xl border border-red-100 bg-red-50 p-4">
                    <div className="font-semibold text-red-800">Risk flags</div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-red-700">{selected.readiness.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul>
                  </div>
                )}
                <div className="mt-5 grid gap-3 sm:grid-cols-3 text-sm">
                  <div className="rounded-xl bg-gray-50 p-3"><div className="text-xs text-gray-500">Project total</div><div className="font-semibold">{money(selected.readiness.budget.project_total, selected.project.budget_currency || "NGN")}</div></div>
                  <div className="rounded-xl bg-gray-50 p-3"><div className="text-xs text-gray-500">Allocated to WPs</div><div className="font-semibold">{money(selected.readiness.budget.work_package_total, selected.project.budget_currency || "NGN")}</div></div>
                  <div className="rounded-xl bg-gray-50 p-3"><div className="text-xs text-gray-500">Unallocated</div><div className="font-semibold">{money(selected.readiness.budget.unallocated, selected.project.budget_currency || "NGN")}</div></div>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="card">
                  <h3 className="text-lg font-bold text-forest-800">Consortium partners</h3>
                  <div className="mt-3 space-y-2">
                    <input className="input" placeholder="Organisation" value={partner.organization} onChange={(e) => setPartner((v) => ({ ...v, organization: e.target.value }))} />
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input className="input" placeholder="Country" value={partner.country} onChange={(e) => setPartner((v) => ({ ...v, country: e.target.value }))} />
                      <select className="input" value={partner.status} onChange={(e) => setPartner((v) => ({ ...v, status: e.target.value }))}>
                        <option value="prospect">Prospect</option><option value="contacted">Contacted</option><option value="interested">Interested</option><option value="committed">Committed</option><option value="confirmed">Confirmed</option><option value="declined">Declined</option>
                      </select>
                    </div>
                    <select className="input" value={partner.partner_type} onChange={(e) => setPartner((v) => ({ ...v, partner_type: e.target.value }))}>
                      <option value="university">University</option><option value="hospital">Hospital</option><option value="government">Government</option><option value="ngo">NGO</option><option value="industry">Industry</option><option value="sme">SME</option><option value="research_institute">Research institute</option><option value="community">Community</option><option value="other">Other</option>
                    </select>
                    <textarea className="input min-h-20" placeholder="Proposed role" value={partner.proposed_role} onChange={(e) => setPartner((v) => ({ ...v, proposed_role: e.target.value }))} />
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input className="input" placeholder="Lead contact" value={partner.lead_contact} onChange={(e) => setPartner((v) => ({ ...v, lead_contact: e.target.value }))} />
                      <input className="input" type="email" placeholder="Email" value={partner.contact_email} onChange={(e) => setPartner((v) => ({ ...v, contact_email: e.target.value }))} />
                    </div>
                    <button className="btn-primary w-full" disabled={action === "partners" || partner.organization.length < 2} onClick={() => addRelated("partners", {
                      ...partner,
                      country: partner.country || null,
                      proposed_role: partner.proposed_role || null,
                      lead_contact: partner.lead_contact || null,
                      contact_email: partner.contact_email || null,
                    })}>Add partner</button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {selected.partners.map((row) => (
                      <div key={row.id} className="rounded-xl bg-cream p-3 text-sm">
                        <div className="flex justify-between gap-2"><strong>{row.organization}</strong><span className="text-xs">{titleCase(row.status)}</span></div>
                        <div className="mt-1 text-xs text-gray-500">{row.country || "Country not set"} · {titleCase(row.partner_type)}</div>
                        {row.proposed_role && <p className="mt-2 text-xs text-gray-600">{row.proposed_role}</p>}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <h3 className="text-lg font-bold text-forest-800">Work packages & budget</h3>
                  <div className="mt-3 space-y-2">
                    <div className="grid gap-2 sm:grid-cols-[80px_1fr]">
                      <input className="input" type="number" min="1" value={workPackage.sequence} onChange={(e) => setWorkPackage((v) => ({ ...v, sequence: e.target.value }))} />
                      <input className="input" placeholder="Work package title" value={workPackage.title} onChange={(e) => setWorkPackage((v) => ({ ...v, title: e.target.value }))} />
                    </div>
                    <input className="input" placeholder="Lead partner" value={workPackage.lead_partner} onChange={(e) => setWorkPackage((v) => ({ ...v, lead_partner: e.target.value }))} />
                    <textarea className="input min-h-20" placeholder="Objective" value={workPackage.objective} onChange={(e) => setWorkPackage((v) => ({ ...v, objective: e.target.value }))} />
                    <textarea className="input min-h-20" placeholder="Outputs — one per line" value={workPackage.outputs} onChange={(e) => setWorkPackage((v) => ({ ...v, outputs: e.target.value }))} />
                    <input className="input" type="number" placeholder="Budget amount" value={workPackage.budget_amount} onChange={(e) => setWorkPackage((v) => ({ ...v, budget_amount: e.target.value }))} />
                    <button className="btn-primary w-full" disabled={action === "work-packages" || workPackage.title.length < 2} onClick={() => addRelated("work-packages", {
                      title: workPackage.title,
                      sequence: Number(workPackage.sequence),
                      lead_partner: workPackage.lead_partner || null,
                      objective: workPackage.objective || null,
                      outputs: workPackage.outputs.split("\n").map((value) => value.trim()).filter(Boolean),
                      budget_amount: workPackage.budget_amount ? Number(workPackage.budget_amount) : 0,
                    })}>Add work package</button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {selected.work_packages.map((row) => (
                      <div key={row.id} className="rounded-xl bg-cream p-3 text-sm">
                        <div className="flex justify-between gap-2"><strong>WP{row.sequence}: {row.title}</strong><span className="text-xs">{row.budget_percent ?? "—"}%</span></div>
                        <div className="mt-1 text-xs text-gray-500">{money(row.budget_amount, selected.project.budget_currency || "NGN")} · {row.lead_partner || "Lead not assigned"}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                <div className="card border border-gold-200">
                  <h3 className="text-lg font-bold text-forest-800">Background IP register</h3>
                  <p className="mt-1 text-xs text-gray-500">Record pre-existing assets before wider institutional or consortium disclosure. This is an evidence trail, not a substitute for legal advice or registration where required.</p>
                  <div className="mt-3 space-y-2">
                    <input className="input" placeholder="Asset title" value={ipAsset.title} onChange={(e) => setIpAsset((v) => ({ ...v, title: e.target.value }))} />
                    <select className="input" value={ipAsset.category} onChange={(e) => setIpAsset((v) => ({ ...v, category: e.target.value }))}>
                      <option value="background_ip">Background IP</option><option value="proposal">Proposal / concept document</option><option value="software">Software</option><option value="method">Method / workflow</option><option value="dataset">Dataset</option><option value="partner_relationship">Partner relationship</option><option value="other">Other</option>
                    </select>
                    <textarea className="input min-h-24" placeholder="Ownership/origin statement" value={ipAsset.ownership_statement} onChange={(e) => setIpAsset((v) => ({ ...v, ownership_statement: e.target.value }))} />
                    <input className="input" placeholder="Evidence reference: dated email, repository commit, document ID…" value={ipAsset.evidence_reference} onChange={(e) => setIpAsset((v) => ({ ...v, evidence_reference: e.target.value }))} />
                    <select className="input" value={ipAsset.disclosure_level} onChange={(e) => setIpAsset((v) => ({ ...v, disclosure_level: e.target.value }))}>
                      <option value="private">Private</option><option value="summary_only">Summary only</option><option value="controlled">Controlled</option><option value="full_after_agreement">Full only after agreement</option>
                    </select>
                    <button className="btn-primary w-full" disabled={action === "ip-assets" || ipAsset.title.length < 2 || ipAsset.ownership_statement.length < 10} onClick={() => addRelated("ip-assets", {
                      ...ipAsset,
                      evidence_reference: ipAsset.evidence_reference || null,
                    })}>Record background asset</button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {selected.ip_assets.map((row) => (
                      <div key={row.id} className="rounded-xl bg-cream p-3 text-sm">
                        <div className="flex justify-between gap-2"><strong>{row.title}</strong><span className="text-xs">{titleCase(row.disclosure_level)}</span></div>
                        <div className="mt-1 text-xs text-gray-500">{titleCase(row.category)} · Pre-collaboration: {row.created_before_collaboration ? "Yes" : "No"}</div>
                        <p className="mt-2 text-xs text-gray-600">{row.ownership_statement}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card border border-gold-200">
                  <h3 className="text-lg font-bold text-forest-800">Controlled disclosure ledger</h3>
                  <p className="mt-1 text-xs text-gray-500">Log substantial disclosures. A watermark alone does not create confidentiality obligations.</p>
                  <div className="mt-3 space-y-2">
                    <input className="input" placeholder="Recipient name" value={disclosure.recipient_name} onChange={(e) => setDisclosure((v) => ({ ...v, recipient_name: e.target.value }))} />
                    <input className="input" placeholder="Recipient organisation" value={disclosure.recipient_organization} onChange={(e) => setDisclosure((v) => ({ ...v, recipient_organization: e.target.value }))} />
                    <input className="input" type="datetime-local" value={disclosure.disclosed_at} onChange={(e) => setDisclosure((v) => ({ ...v, disclosed_at: e.target.value }))} />
                    <div className="grid gap-2 sm:grid-cols-[1fr_100px]">
                      <input className="input" placeholder="Material disclosed" value={disclosure.material} onChange={(e) => setDisclosure((v) => ({ ...v, material: e.target.value }))} />
                      <input className="input" placeholder="Version" value={disclosure.version} onChange={(e) => setDisclosure((v) => ({ ...v, version: e.target.value }))} />
                    </div>
                    <textarea className="input min-h-20" placeholder="Purpose" value={disclosure.purpose} onChange={(e) => setDisclosure((v) => ({ ...v, purpose: e.target.value }))} />
                    <textarea className="input min-h-20" placeholder="Confidentiality/non-use basis: NDA, MOU clause, confidential-meeting acknowledgement…" value={disclosure.confidentiality_basis} onChange={(e) => setDisclosure((v) => ({ ...v, confidentiality_basis: e.target.value }))} />
                    <button className="btn-primary w-full" disabled={action === "disclosures" || disclosure.recipient_name.length < 2 || disclosure.material.length < 2} onClick={() => addRelated("disclosures", {
                      ...disclosure,
                      recipient_organization: disclosure.recipient_organization || null,
                      disclosed_at: new Date(disclosure.disclosed_at).toISOString(),
                      version: disclosure.version || null,
                      purpose: disclosure.purpose || null,
                      confidentiality_basis: disclosure.confidentiality_basis || null,
                      notes: disclosure.notes || null,
                    })}>Log disclosure</button>
                  </div>
                  <div className="mt-4 space-y-2">
                    {selected.disclosures.map((row) => (
                      <div key={row.id} className="rounded-xl bg-cream p-3 text-sm">
                        <div className="flex justify-between gap-2"><strong>{row.recipient_name}</strong><span className="text-xs">{row.version || ""}</span></div>
                        <div className="mt-1 text-xs text-gray-500">{row.recipient_organization || "No organisation"} · {row.disclosed_at ? new Date(row.disclosed_at).toLocaleString() : ""}</div>
                        <p className="mt-2 text-xs text-gray-600">{row.material}</p>
                        {!row.confidentiality_basis && <div className="mt-2 text-xs font-semibold text-red-700">No confidentiality basis recorded</div>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 className="text-lg font-bold text-forest-800">Critical-path milestones</h3>
                <div className="mt-3 grid gap-2 md:grid-cols-3">
                  <input className="input" placeholder="Milestone" value={milestone.title} onChange={(e) => setMilestone((v) => ({ ...v, title: e.target.value }))} />
                  <input className="input" type="date" value={milestone.due_on} onChange={(e) => setMilestone((v) => ({ ...v, due_on: e.target.value }))} />
                  <input className="input" placeholder="Owner" value={milestone.owner} onChange={(e) => setMilestone((v) => ({ ...v, owner: e.target.value }))} />
                </div>
                <div className="mt-2 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
                  <select className="input" value={milestone.milestone_type} onChange={(e) => setMilestone((v) => ({ ...v, milestone_type: e.target.value }))}>
                    <option value="proposal">Proposal</option><option value="partnership">Partnership</option><option value="ethics">Ethics</option><option value="scientific">Scientific</option><option value="financial">Financial</option><option value="submission">Submission</option><option value="other">Other</option>
                  </select>
                  <select className="input" value={milestone.status} onChange={(e) => setMilestone((v) => ({ ...v, status: e.target.value }))}>
                    <option value="planned">Planned</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="blocked">Blocked</option>
                  </select>
                  <button className="btn-primary" disabled={action === "milestones" || milestone.title.length < 2} onClick={() => addRelated("milestones", {
                    ...milestone,
                    due_on: milestone.due_on || null,
                    owner: milestone.owner || null,
                    evidence: milestone.evidence || null,
                  })}>Add milestone</button>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {selected.milestones.map((row) => (
                    <div key={row.id} className="rounded-xl border border-gray-100 p-3 text-sm">
                      <div className="flex justify-between gap-2"><strong>{row.title}</strong><span className="text-xs">{titleCase(row.status)}</span></div>
                      <div className="mt-1 text-xs text-gray-500">{titleCase(row.milestone_type)} · {row.due_on || "No date"} · {row.owner || "Owner not assigned"}</div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-red-100 bg-red-50 p-5 text-sm leading-6 text-red-800">
                <strong>Protection boundary:</strong> this Studio creates a dated operational record and helps control disclosure; it does not itself create patent rights, guarantee ownership, or replace an NDA/MOU/IP agreement, funder rules, institutional policy or qualified legal review.
              </div>
            </>
          ) : (
            <div className="card py-20 text-center text-gray-400">Create or select a grant project to open the consortium and protection workspace.</div>
          )}
        </div>
      </section>
    </div>
  );
}
