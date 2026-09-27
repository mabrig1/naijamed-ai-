import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge } from "../components/Layout";

type OfficialSource = {
  id: string;
  organization: string;
  title: string;
  status: string;
  issued?: string | null;
  url?: string | null;
  topic: string;
  summary: string;
};

type Review = {
  id: string;
  title: string;
  research_question: string;
  paper_count: number;
};

type Account = {
  is_pro: boolean;
  copilot_workspace_count: number;
  copilot_draft_count: number;
  copilot_workspace_limit: number | null;
  copilot_draft_limit: number | null;
};

type SourcesPayload = {
  official_sources: OfficialSource[];
  reviews: Review[];
  account: Account;
};

type WorkspaceSummary = {
  id: string;
  title: string;
  purpose: string;
  objective: string;
  jurisdiction?: string | null;
  nofo_url?: string | null;
  official_source_ids: string[];
  review_ids: string[];
  notes?: string | null;
  draft_count: number;
  updated_at?: string | null;
};

type HomePayload = {
  workspaces: WorkspaceSummary[];
  account: Account;
};

type Gap = { area: string; status: string; note: string };

type Draft = {
  id: string;
  purpose: string;
  content: string;
  generation_method: string;
  cited_source_ids: string[];
  source_snapshot: OfficialSource[];
  gap_check: Gap[];
  created_at?: string | null;
};

type WorkspaceDetail = {
  workspace: WorkspaceSummary & {
    custom_sources?: Array<{ id: string; title: string; url?: string | null; excerpt: string; status: string }>;
  };
  drafts: Draft[];
  account: Account;
};

const PURPOSES = [
  ["specific_aims", "NIH Specific Aims"],
  ["research_strategy", "NIH Research Strategy"],
  ["grant_plan", "Grant application plan"],
  ["regulatory_brief", "Regulatory strategy brief"],
  ["ctd_plan", "CTD / eCTD dossier plan"],
  ["protocol_outline", "Clinical / research protocol outline"],
  ["compliance_gap", "Compliance gap analysis"],
];

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function statusClass(status: string) {
  if (status === "final" || status === "current_instructions" || status === "current_guidance") return "bg-forest-50 text-forest-700";
  if (status === "draft") return "bg-amber-50 text-amber-700";
  return "bg-gray-100 text-gray-600";
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export default function FormularyCopilot() {
  const [sources, setSources] = useState<SourcesPayload | null>(null);
  const [home, setHome] = useState<HomePayload | null>(null);
  const [selected, setSelected] = useState<WorkspaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [instruction, setInstruction] = useState("");
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [form, setForm] = useState({
    title: "",
    purpose: "specific_aims",
    objective: "",
    jurisdiction: "",
    nofo_url: "",
    official_source_ids: [] as string[],
    review_ids: [] as string[],
    notes: "",
    custom_title: "",
    custom_url: "",
    custom_excerpt: "",
  });

  async function loadHome() {
    const [{ data: sourceData }, { data: homeData }] = await Promise.all([
      api.get<SourcesPayload>("/api/formulary/copilot/sources"),
      api.get<HomePayload>("/api/formulary/copilot"),
    ]);
    setSources(sourceData);
    setHome(homeData);
    return homeData;
  }

  async function loadWorkspace(id: string) {
    setAction("workspace");
    setError("");
    try {
      const { data } = await api.get<WorkspaceDetail>(`/api/formulary/copilot/workspaces/${id}`);
      setSelected(data);
      setGaps(data.drafts[0]?.gap_check ?? []);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  useEffect(() => {
    loadHome()
      .then((payload) => {
        if (payload.workspaces[0]) return loadWorkspace(payload.workspaces[0].id);
        return undefined;
      })
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggle(list: "official_source_ids" | "review_ids", id: string) {
    setForm((current) => ({
      ...current,
      [list]: current[list].includes(id)
        ? current[list].filter((value) => value !== id)
        : [...current[list], id],
    }));
  }

  async function createWorkspace() {
    setAction("create");
    setError("");
    setMessage("");
    try {
      const custom_sources = form.custom_excerpt.trim()
        ? [{
            title: form.custom_title.trim() || "User-supplied source",
            url: form.custom_url.trim() || null,
            excerpt: form.custom_excerpt.trim(),
            status: "user_supplied",
          }]
        : [];
      const { data } = await api.post<WorkspaceSummary>("/api/formulary/copilot/workspaces", {
        title: form.title,
        purpose: form.purpose,
        objective: form.objective,
        jurisdiction: form.jurisdiction || null,
        nofo_url: form.nofo_url || null,
        official_source_ids: form.official_source_ids,
        review_ids: form.review_ids,
        custom_sources,
        notes: form.notes || null,
      });
      setMessage("Regulatory / grant workspace created.");
      setForm({
        title: "",
        purpose: "specific_aims",
        objective: "",
        jurisdiction: "",
        nofo_url: "",
        official_source_ids: [],
        review_ids: [],
        notes: "",
        custom_title: "",
        custom_url: "",
        custom_excerpt: "",
      });
      await loadHome();
      await loadWorkspace(data.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function runGapCheck() {
    if (!selected) return;
    setAction("gap");
    setError("");
    try {
      const { data } = await api.get<{ gaps: Gap[] }>(`/api/formulary/copilot/workspaces/${selected.workspace.id}/gap-check`);
      setGaps(data.gaps);
      setMessage("Gap check refreshed.");
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function generateDraft() {
    if (!selected) return;
    setAction("draft");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<Draft>(`/api/formulary/copilot/workspaces/${selected.workspace.id}/draft`, {
        instruction: instruction.trim() || null,
      });
      setMessage(`Draft generated with ${data.cited_source_ids.length} cited source(s).`);
      setInstruction("");
      await loadWorkspace(selected.workspace.id);
      await loadHome();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  const latestDraft = selected?.drafts[0] ?? null;
  const officialById = useMemo(
    () => new Map((sources?.official_sources ?? []).map((source) => [source.id, source])),
    [sources],
  );

  if (loading && !sources) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  if (error && !sources) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary Regulatory & Grant Copilot</div>
            <h1 className="mt-3 text-4xl font-bold">Draft against sources you can inspect—not invisible model memory.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Select current FDA, ICH and NIH references, link your Living Review, add your exact NOFO or guidance excerpt, then generate a working draft with source IDs and unresolved checks preserved.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5 text-sm">
            <div className="grid grid-cols-2 gap-5">
              <div><div className="text-xs text-forest-200">Workspaces</div><div className="mt-1 text-2xl font-bold text-gold-300">{sources?.account.copilot_workspace_count ?? 0}</div></div>
              <div><div className="text-xs text-forest-200">Drafts</div><div className="mt-1 text-2xl font-bold text-gold-300">{sources?.account.copilot_draft_count ?? 0}</div></div>
            </div>
            <div className="mt-3 text-xs text-forest-200">
              {sources?.account.is_pro
                ? "Unlimited with Formulary Scholar"
                : `Free: ${sources?.account.copilot_workspace_limit ?? 0} workspace · ${sources?.account.copilot_draft_limit ?? 0} drafts`}
            </div>
            {!sources?.account.is_pro && <Link to="/pricing" className="mt-4 block rounded-xl bg-gold-400 px-4 py-2.5 text-center font-bold text-forest-900">Upgrade to Scholar</Link>}
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link className="btn-outline" to="/formulary">← Living Review</Link>
        <Link className="btn-outline" to="/formulary/pkpd">PK/PD Simulator</Link>
        <Link className="btn-outline" to="/formulary/portfolio">Portfolio Tracker</Link>
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 xl:grid-cols-[0.82fr_1.18fr]">
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Create workspace</h2>
            <div className="mt-4 space-y-4">
              <input className="input" placeholder="Workspace title" value={form.title} onChange={(e) => setForm((v) => ({ ...v, title: e.target.value }))} />
              <select className="input" value={form.purpose} onChange={(e) => setForm((v) => ({ ...v, purpose: e.target.value }))}>
                {PURPOSES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <textarea className="input min-h-28" placeholder="Research / regulatory objective" value={form.objective} onChange={(e) => setForm((v) => ({ ...v, objective: e.target.value }))} />
              <div className="grid gap-3 sm:grid-cols-2">
                <input className="input" placeholder="Jurisdiction / regulator, e.g. FDA" value={form.jurisdiction} onChange={(e) => setForm((v) => ({ ...v, jurisdiction: e.target.value }))} />
                <input className="input" placeholder="NOFO or agency URL, optional" value={form.nofo_url} onChange={(e) => setForm((v) => ({ ...v, nofo_url: e.target.value }))} />
              </div>

              <div>
                <div className="label">Official sources</div>
                <div className="max-h-72 space-y-2 overflow-y-auto rounded-2xl border border-gray-100 p-2">
                  {sources?.official_sources.map((source) => (
                    <label key={source.id} className="flex cursor-pointer items-start gap-3 rounded-xl p-3 hover:bg-cream">
                      <input type="checkbox" className="mt-1" checked={form.official_source_ids.includes(source.id)} onChange={() => toggle("official_source_ids", source.id)} />
                      <span className="min-w-0">
                        <span className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-gray-900">{source.organization} · {source.title}</span>
                          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusClass(source.status)}`}>{source.status}</span>
                        </span>
                        <span className="mt-1 block text-xs leading-5 text-gray-500">{source.summary}</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <div className="label">Link Living Review evidence</div>
                <div className="space-y-2">
                  {sources?.reviews.length ? sources.reviews.map((review) => (
                    <label key={review.id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-100 p-3">
                      <input type="checkbox" className="mt-1" checked={form.review_ids.includes(review.id)} onChange={() => toggle("review_ids", review.id)} />
                      <span><span className="block text-sm font-semibold">{review.title}</span><span className="text-xs text-gray-500">{review.paper_count} paper(s) · {review.research_question}</span></span>
                    </label>
                  )) : <div className="text-sm text-gray-400">No Living Review available yet.</div>}
                </div>
              </div>

              <div className="rounded-2xl bg-cream p-4">
                <div className="font-semibold text-forest-800">Custom NOFO / guidance excerpt</div>
                <p className="mt-1 text-xs text-gray-500">Paste the exact relevant passage. Formulary will not assume what a URL contains.</p>
                <div className="mt-3 space-y-2">
                  <input className="input" placeholder="Source title" value={form.custom_title} onChange={(e) => setForm((v) => ({ ...v, custom_title: e.target.value }))} />
                  <input className="input" placeholder="Source URL, optional" value={form.custom_url} onChange={(e) => setForm((v) => ({ ...v, custom_url: e.target.value }))} />
                  <textarea className="input min-h-28" placeholder="Paste relevant source excerpt" value={form.custom_excerpt} onChange={(e) => setForm((v) => ({ ...v, custom_excerpt: e.target.value }))} />
                </div>
              </div>

              <textarea className="input min-h-24" placeholder="Researcher notes / constraints" value={form.notes} onChange={(e) => setForm((v) => ({ ...v, notes: e.target.value }))} />
              <button className="btn-primary w-full" disabled={action === "create" || form.title.length < 3 || form.objective.length < 20} onClick={createWorkspace}>
                {action === "create" ? "Creating…" : "Create grounded workspace"}
              </button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-bold text-forest-800">Your workspaces</h2>
            <div className="mt-4 space-y-2">
              {home?.workspaces.length ? home.workspaces.map((workspace) => (
                <button key={workspace.id} type="button" onClick={() => loadWorkspace(workspace.id)} className={`w-full rounded-xl border p-3 text-left ${selected?.workspace.id === workspace.id ? "border-forest-500 bg-forest-50" : "border-gray-100 hover:border-forest-200"}`}>
                  <div className="font-semibold text-gray-900">{workspace.title}</div>
                  <div className="mt-1 text-xs text-gray-500">{titleCase(workspace.purpose)} · {workspace.draft_count} draft(s)</div>
                </button>
              )) : <p className="text-sm text-gray-400">No copilot workspace yet.</p>}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {selected ? (
            <>
              <div className="card">
                <div className="text-xs font-bold uppercase tracking-wide text-forest-500">{titleCase(selected.workspace.purpose)}</div>
                <h2 className="mt-1 text-2xl font-bold text-gray-900">{selected.workspace.title}</h2>
                <p className="mt-3 text-sm leading-6 text-gray-600">{selected.workspace.objective}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {selected.workspace.official_source_ids.map((id) => {
                    const source = officialById.get(id);
                    return <span key={id} className="rounded-full bg-forest-50 px-3 py-1 text-xs text-forest-700">{source?.organization ?? "Source"} · {source?.title ?? id}</span>;
                  })}
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  <button className="btn-outline" disabled={action === "gap"} onClick={runGapCheck}>{action === "gap" ? "Checking…" : "Run gap check"}</button>
                  {selected.workspace.nofo_url && <a className="btn-outline" href={selected.workspace.nofo_url} target="_blank" rel="noreferrer">Open NOFO / source</a>}
                </div>
              </div>

              {!!gaps.length && (
                <div className="card">
                  <h3 className="text-lg font-bold text-forest-800">Compliance / submission gaps</h3>
                  <div className="mt-4 space-y-3">
                    {gaps.map((gap) => (
                      <div key={gap.area} className="rounded-xl border border-gray-100 p-4">
                        <div className="flex items-center justify-between gap-3">
                          <span className="font-semibold text-gray-900">{gap.area}</span>
                          <StatusBadge status={gap.status === "covered" || gap.status === "present" ? "active" : gap.status === "warning" ? "pending" : "draft"} />
                        </div>
                        <p className="mt-2 text-sm leading-6 text-gray-600">{gap.note}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="card">
                <h3 className="text-lg font-bold text-forest-800">Generate grounded draft</h3>
                <p className="mt-2 text-sm text-gray-500">Optional instruction can narrow this version without changing the saved source set.</p>
                <textarea className="input mt-4 min-h-24" value={instruction} onChange={(e) => setInstruction(e.target.value)} placeholder="e.g. Focus the Specific Aims on CYP3A4 inhibition in pediatrics; do not invent preliminary data." />
                <button className="btn-primary mt-3 w-full" disabled={action === "draft"} onClick={generateDraft}>{action === "draft" ? "Generating…" : "Generate source-grounded draft"}</button>
              </div>

              {latestDraft ? (
                <>
                  <div className="card">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs font-bold uppercase tracking-wide text-forest-500">Latest working draft</div>
                        <div className="mt-1 text-xs text-gray-400">{latestDraft.generation_method} · {latestDraft.cited_source_ids.length} cited source(s)</div>
                      </div>
                      <button className="btn-outline text-sm" onClick={() => navigator.clipboard.writeText(latestDraft.content)}>Copy draft</button>
                    </div>
                    <pre className="mt-5 whitespace-pre-wrap rounded-2xl bg-cream p-5 font-sans text-sm leading-7 text-gray-800">{latestDraft.content}</pre>
                  </div>

                  <div className="card">
                    <h3 className="text-lg font-bold text-forest-800">Source snapshot saved with this draft</h3>
                    <div className="mt-4 space-y-3">
                      {latestDraft.source_snapshot.map((source) => (
                        <div key={source.id} className="rounded-xl border border-gray-100 p-4">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-gray-900">[SRC:{source.id}] {source.title}</span>
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusClass(source.status)}`}>{source.status}</span>
                          </div>
                          <p className="mt-2 text-xs leading-5 text-gray-500">{source.summary}</p>
                          {source.url && <a href={source.url} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs text-forest-700 underline">Open source</a>}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : <div className="card py-16 text-center text-gray-400">Generate a draft to see the source snapshot and citations.</div>}
            </>
          ) : <div className="card py-20 text-center text-gray-400">Create or select a workspace to begin.</div>}
        </div>
      </section>

      <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
        <strong>Submission boundary:</strong> Formulary produces editable working drafts. The current NOFO, regulator, regional implementation documents, institutional research office, ethics requirements and professional review remain authoritative. Draft guidance must not be represented as final policy.
      </section>
    </div>
  );
}
