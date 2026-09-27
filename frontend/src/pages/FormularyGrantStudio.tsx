import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge, ProgressBar } from "../components/Layout";
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
  partner_count?: number;
  work_package_count?: number;
  background_ip_count?: number;
  disclosure_count?: number;
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
    return new Intl.NumberFormat("en-NG", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${currency} ${new Intl.NumberFormat().format(amount)}`;
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
    organization: "", country: "", partner_type: "university", status: "prospect",
    proposed_role: "", lead_contact: "", contact_email: "",
  });
  const [wp, setWp] = useState({
    title: "", sequence: "1", lead_partner: "", objective: "", outputs: "", budget_amount: "",
  });
  const [milestone, setMilestone] = useState({
    title: "", milestone_type: "proposal", due_on: "", status: "planned", owner: "", evidence: "",
  });
  const [ip, setIp] = useState({
    title: "", category: "background_ip", ownership_statement: "", evidence_reference: "",
    created_before_collaboration: true, disclosure_level: "controlled",
  });
  const [disclosure, setDisclosure] = useState({
    recipient_name: "", recipient_organization: "", disclosed_at: new Date().toISOString().slice(0, 16),
    material: "", version: "v1.0", purpose: "", confidentiality_basis: "", notes: "",
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
      setWp((current) => ({ ...current, sequence: String((data.work_packages?.length ?? 0) + 1) }));
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
    setMessage("NEXUS-AMR Africa template loaded. Add the exact funder/call only after verifying the live opportunity.");
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

  async function addRelated(kind: "partners" | "work-packages" | "milestones" | "ip-assets" | "disclosures", payload: Record<string, unknown>) {
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

}
