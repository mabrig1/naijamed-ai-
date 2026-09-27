import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge } from "../components/Layout";

type Profile = {
  track?: string | null;
  program_name?: string | null;
  institution?: string | null;
  specialty?: string | null;
  start_date?: string | null;
  target_end_date?: string | null;
  summary?: string | null;
  competencies?: string[];
  public_enabled?: boolean;
  public_slug?: string | null;
};

type Item = {
  id: string;
  category: string;
  title: string;
  description?: string | null;
  occurred_on: string;
  status: string;
  competencies: string[];
  hours?: number | null;
  outcome?: string | null;
  evidence_url?: string | null;
  visibility: string;
  attestation_status: string;
  attested_by?: { name?: string; title?: string; organization?: string } | null;
  attested_at?: string | null;
};

type Payload = {
  profile: Profile;
  items: Item[];
  summary: {
    total_items: number;
    completed_items: number;
    attested_items: number;
    total_hours: number;
    by_category: Record<string, number>;
    by_status: Record<string, number>;
    competency_activity: Record<string, number>;
  };
  account: {
    is_pro: boolean;
    portfolio_item_count: number;
    portfolio_item_limit: number | null;
  };
};

const CATEGORIES = [
  ["rotation", "Rotation / learning experience"],
  ["clinical_intervention", "Clinical intervention"],
  ["development_plan", "Development plan"],
  ["evaluation", "Evaluation"],
  ["research_milestone", "Research milestone"],
  ["committee", "Thesis / committee milestone"],
  ["presentation", "Presentation / journal club"],
  ["publication", "Publication"],
  ["grant", "Grant / fellowship"],
  ["teaching", "Teaching"],
  ["certification", "Certification"],
  ["coursework", "Coursework"],
  ["experiment", "Experiment / lab milestone"],
  ["other", "Other"],
];

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function splitList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export default function FormularyPortfolio() {
  const [data, setData] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [profile, setProfile] = useState({
    track: "residency",
    program_name: "",
    institution: "",
    specialty: "",
    start_date: "",
    target_end_date: "",
    summary: "",
    competencies: "",
    public_enabled: false,
    public_slug: "",
  });
  const [item, setItem] = useState({
    category: "rotation",
    title: "",
    description: "",
    occurred_on: new Date().toISOString().slice(0, 10),
    status: "completed",
    competencies: "",
    hours: "",
    outcome: "",
    evidence_url: "",
    visibility: "private",
  });
  const [attest, setAttest] = useState({
    item_id: "",
    verifier_name: "",
    verifier_email: "",
    message: "",
  });

  async function load() {
    setLoading(true);
    try {
      const { data: payload } = await api.get<Payload>("/api/formulary/portfolio");
      setData(payload);
      setProfile({
        track: payload.profile.track || "residency",
        program_name: payload.profile.program_name || "",
        institution: payload.profile.institution || "",
        specialty: payload.profile.specialty || "",
        start_date: payload.profile.start_date || "",
        target_end_date: payload.profile.target_end_date || "",
        summary: payload.profile.summary || "",
        competencies: (payload.profile.competencies || []).join(", "),
        public_enabled: Boolean(payload.profile.public_enabled),
        public_slug: payload.profile.public_slug || "",
      });
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function saveProfile() {
    setAction("profile");
    setError("");
    setMessage("");
    try {
      const { data: payload } = await api.put<Payload>("/api/formulary/portfolio/profile", {
        ...profile,
        start_date: profile.start_date || null,
        target_end_date: profile.target_end_date || null,
        specialty: profile.specialty || null,
        summary: profile.summary || null,
        public_slug: profile.public_slug || null,
        competencies: splitList(profile.competencies),
      });
      setData(payload);
      setProfile((current) => ({ ...current, public_slug: payload.profile.public_slug || "" }));
      setMessage("Portfolio profile saved.");
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function addItem() {
    setAction("item");
    setError("");
    setMessage("");
    try {
      await api.post("/api/formulary/portfolio/items", {
        ...item,
        competencies: splitList(item.competencies),
        hours: item.hours ? Number(item.hours) : null,
        evidence_url: item.evidence_url || null,
        description: item.description || null,
        outcome: item.outcome || null,
      });
      setItem((current) => ({
        ...current,
        title: "",
        description: "",
        competencies: "",
        hours: "",
        outcome: "",
        evidence_url: "",
      }));
      setMessage("Portfolio activity saved.");
      await load();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function createAttestation() {
    if (!attest.item_id) return;
    setAction("attest");
    setError("");
    setMessage("");
    try {
      const { data: response } = await api.post<{ attestation_path: string; expires_at: string }>("/api/formulary/portfolio/attestations", attest);
      const fullUrl = `${window.location.origin}${response.attestation_path}`;
      try { await navigator.clipboard.writeText(fullUrl); } catch { /* user can copy from message */ }
      setMessage(`Attestation link created and copied: ${fullUrl}`);
      setAttest({ item_id: "", verifier_name: "", verifier_email: "", message: "" });
      await load();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  const publicUrl = data?.profile.public_enabled && data.profile.public_slug
    ? `${window.location.origin}/portfolio/${data.profile.public_slug}`
    : "";

  const competencyRows = useMemo(
    () => Object.entries(data?.summary.competency_activity || {}).sort((a, b) => b[1] - a[1]),
    [data],
  );

  if (loading && !data) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  if (error && !data) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary Portfolio</div>
            <h1 className="mt-3 text-4xl font-bold">Track rotations, research milestones and professional growth in one record.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Built for PharmD learners, pharmacy residents, M.Sc. and Ph.D. researchers. Use your own competency framework instead of being locked to one institution.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5 text-sm">
            <div className="text-xs text-forest-200">Portfolio items</div>
            <div className="mt-1 text-3xl font-bold text-gold-300">{data?.account.portfolio_item_count ?? 0}</div>
            <div className="mt-1 text-xs text-forest-200">
              {data?.account.is_pro ? "Unlimited with Formulary Scholar" : `Free limit: ${data?.account.portfolio_item_limit ?? 0}`}
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link className="btn-outline" to="/formulary">← Living Review</Link>
        <Link className="btn-outline" to="/formulary/pkpd">PK/PD Simulator</Link>
        {publicUrl && <a className="btn-primary" href={publicUrl} target="_blank" rel="noreferrer">Open Public Portfolio</a>}
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="card"><div className="text-sm text-gray-500">Total records</div><div className="mt-2 text-3xl font-bold">{data?.summary.total_items ?? 0}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Completed</div><div className="mt-2 text-3xl font-bold">{data?.summary.completed_items ?? 0}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Supervisor-attested</div><div className="mt-2 text-3xl font-bold">{data?.summary.attested_items ?? 0}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Logged hours</div><div className="mt-2 text-3xl font-bold">{data?.summary.total_hours ?? 0}</div></div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Program profile</h2>
            <div className="mt-4 space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="label">Track</label>
                  <select className="input" value={profile.track} onChange={(e) => setProfile((v) => ({ ...v, track: e.target.value }))}>
                    <option value="pharmd">PharmD</option>
                    <option value="residency">Residency</option>
                    <option value="msc">M.Sc.</option>
                    <option value="phd">Ph.D.</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div><label className="label">Specialty</label><input className="input" value={profile.specialty} onChange={(e) => setProfile((v) => ({ ...v, specialty: e.target.value }))} placeholder="e.g. oncology pharmacy, pharmacology" /></div>
              </div>
              <input className="input" value={profile.program_name} onChange={(e) => setProfile((v) => ({ ...v, program_name: e.target.value }))} placeholder="Program / degree name" />
              <input className="input" value={profile.institution} onChange={(e) => setProfile((v) => ({ ...v, institution: e.target.value }))} placeholder="Institution" />
              <div className="grid gap-3 sm:grid-cols-2">
                <div><label className="label">Start date</label><input className="input" type="date" value={profile.start_date} onChange={(e) => setProfile((v) => ({ ...v, start_date: e.target.value }))} /></div>
                <div><label className="label">Target completion</label><input className="input" type="date" value={profile.target_end_date} onChange={(e) => setProfile((v) => ({ ...v, target_end_date: e.target.value }))} /></div>
              </div>
              <textarea className="input min-h-24" value={profile.summary} onChange={(e) => setProfile((v) => ({ ...v, summary: e.target.value }))} placeholder="Professional / research summary" />
              <textarea className="input min-h-20" value={profile.competencies} onChange={(e) => setProfile((v) => ({ ...v, competencies: e.target.value }))} placeholder="Competencies, comma separated" />
              <label className="flex items-start gap-3 rounded-xl bg-cream p-3 text-sm">
                <input type="checkbox" checked={profile.public_enabled} onChange={(e) => setProfile((v) => ({ ...v, public_enabled: e.target.checked }))} />
                <span>Enable an opt-in public portfolio. Only items individually marked public will appear.</span>
              </label>
              {profile.public_enabled && <input className="input" value={profile.public_slug} onChange={(e) => setProfile((v) => ({ ...v, public_slug: e.target.value }))} placeholder="Public profile slug" />}
              <button className="btn-primary w-full" disabled={action === "profile" || profile.program_name.length < 2 || profile.institution.length < 2} onClick={saveProfile}>{action === "profile" ? "Saving…" : "Save profile"}</button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Competency activity</h2>
            <div className="mt-4 space-y-2">
              {competencyRows.length ? competencyRows.map(([name, count]) => (
                <div key={name} className="flex items-center justify-between rounded-xl bg-cream px-4 py-3">
                  <span className="text-sm font-medium">{name}</span>
                  <span className="text-sm font-bold text-forest-700">{count}</span>
                </div>
              )) : <p className="text-sm text-gray-400">Add competencies to your profile and tag activities to build this view.</p>}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Log activity or milestone</h2>
            <div className="mt-4 space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <select className="input" value={item.category} onChange={(e) => setItem((v) => ({ ...v, category: e.target.value }))}>
                  {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <input className="input" type="date" value={item.occurred_on} onChange={(e) => setItem((v) => ({ ...v, occurred_on: e.target.value }))} />
              </div>
              <input className="input" value={item.title} onChange={(e) => setItem((v) => ({ ...v, title: e.target.value }))} placeholder="Activity or milestone title" />
              <textarea className="input min-h-24" value={item.description} onChange={(e) => setItem((v) => ({ ...v, description: e.target.value }))} placeholder="What happened, your role, context and learning" />
              <div className="grid gap-3 sm:grid-cols-3">
                <select className="input" value={item.status} onChange={(e) => setItem((v) => ({ ...v, status: e.target.value }))}>
                  <option value="planned">Planned</option>
                  <option value="in_progress">In progress</option>
                  <option value="completed">Completed</option>
                </select>
                <input className="input" type="number" min="0" step="0.5" value={item.hours} onChange={(e) => setItem((v) => ({ ...v, hours: e.target.value }))} placeholder="Hours" />
                <select className="input" value={item.visibility} onChange={(e) => setItem((v) => ({ ...v, visibility: e.target.value }))}>
                  <option value="private">Private</option>
                  <option value="public">Public</option>
                </select>
              </div>
              <input className="input" value={item.competencies} onChange={(e) => setItem((v) => ({ ...v, competencies: e.target.value }))} placeholder="Competencies, comma separated" />
              <textarea className="input min-h-20" value={item.outcome} onChange={(e) => setItem((v) => ({ ...v, outcome: e.target.value }))} placeholder="Outcome / reflection" />
              <input className="input" value={item.evidence_url} onChange={(e) => setItem((v) => ({ ...v, evidence_url: e.target.value }))} placeholder="Evidence URL, optional (https://...)" />
              <button className="btn-primary w-full" disabled={action === "item" || item.title.length < 2} onClick={addItem}>{action === "item" ? "Saving…" : "Save activity"}</button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Activity timeline</h2>
            <div className="mt-4 space-y-3">
              {data?.items.length ? data.items.map((record) => (
                <article key={record.id} className="rounded-2xl border border-gray-100 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-forest-500">{titleCase(record.category)} · {record.occurred_on}</div>
                      <h3 className="mt-1 font-bold text-gray-900">{record.title}</h3>
                    </div>
                    <StatusBadge status={record.status === "completed" ? "active" : record.status === "in_progress" ? "pending" : "draft"} />
                  </div>
                  {record.description && <p className="mt-3 text-sm leading-6 text-gray-600">{record.description}</p>}
                  {!!record.competencies.length && <div className="mt-3 flex flex-wrap gap-1.5">{record.competencies.map((name) => <span key={name} className="rounded-full bg-forest-50 px-2.5 py-1 text-xs text-forest-700">{name}</span>)}</div>}
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    {record.hours != null && <span>{record.hours} hours</span>}
                    <span>{record.visibility}</span>
                    <span>Attestation: {record.attestation_status}</span>
                    {record.evidence_url && <a href={record.evidence_url} target="_blank" rel="noreferrer" className="text-forest-700 underline">Evidence</a>}
                  </div>
                  {record.attested_by && <div className="mt-3 rounded-xl bg-forest-50 p-3 text-xs text-forest-800">Attested by {record.attested_by.name}{record.attested_by.title ? `, ${record.attested_by.title}` : ""}{record.attested_by.organization ? ` · ${record.attested_by.organization}` : ""}</div>}
                  <button className="mt-3 text-xs font-semibold text-forest-700 underline" onClick={() => setAttest((v) => ({ ...v, item_id: record.id }))}>Request supervisor attestation</button>
                </article>
              )) : <p className="py-8 text-center text-sm text-gray-400">No portfolio records yet.</p>}
            </div>
          </div>
        </div>
      </section>

      {attest.item_id && (
        <section className="card border border-gold-200">
          <h2 className="text-xl font-bold text-forest-800">Create private attestation link</h2>
          <p className="mt-2 text-sm text-gray-500">The link expires after 14 days. Formulary records the response but does not independently certify the verifier's identity or employment.</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <input className="input" value={attest.verifier_name} onChange={(e) => setAttest((v) => ({ ...v, verifier_name: e.target.value }))} placeholder="Verifier / preceptor name" />
            <input className="input" type="email" value={attest.verifier_email} onChange={(e) => setAttest((v) => ({ ...v, verifier_email: e.target.value }))} placeholder="Verifier email" />
            <textarea className="input min-h-20 md:col-span-2" value={attest.message} onChange={(e) => setAttest((v) => ({ ...v, message: e.target.value }))} placeholder="Optional note to verifier" />
            <button className="btn-primary" disabled={action === "attest" || !attest.verifier_name || !attest.verifier_email} onClick={createAttestation}>{action === "attest" ? "Creating…" : "Create & copy link"}</button>
            <button className="btn-outline" onClick={() => setAttest({ item_id: "", verifier_name: "", verifier_email: "", message: "" })}>Cancel</button>
          </div>
        </section>
      )}

      <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
        <strong>Portfolio boundary:</strong> public visibility is optional and off by default. A supervisor attestation is evidence of a response through the private link; it is not equivalent to university, employer or licensing-board credential verification.
      </section>
    </div>
  );
}
