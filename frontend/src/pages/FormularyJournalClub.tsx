import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge } from "../components/Layout";
import { useAuth } from "../contexts/AuthContext";

type Account = {
  is_pro: boolean;
  journal_room_count: number;
  journal_factcheck_count: number;
  journal_room_limit: number | null;
  journal_factcheck_limit: number | null;
};

type Room = {
  id: string;
  title: string;
  review_id: string;
  entry_ids: string[];
  scheduled_at?: string | null;
  meeting_url?: string | null;
  agenda: string[];
  appraisal_template: string;
  status: "scheduled" | "live" | "closed";
  locked: boolean;
  owner_user_id: string;
  member_count: number;
  created_at?: string | null;
  updated_at?: string | null;
};

type ReviewSummary = {
  id: string;
  title: string;
  research_question: string;
  paper_count: number;
};

type Evidence = {
  id: string;
  title?: string | null;
  doi?: string | null;
  journal?: string | null;
  published?: string | null;
  study_design?: string | null;
  population?: string | null;
  sample_size?: number | null;
  intervention?: string | null;
  comparator?: string | null;
  dosing_regimen?: string[];
  primary_endpoints?: string[];
  p_values?: string[];
  confidence_intervals?: string[];
  adverse_events?: string[];
  pk_parameters?: Record<string, unknown>;
  key_findings?: string[];
  limitations?: string[];
};

type DiscussionItem = {
  id: string;
  kind: string;
  content: string;
  entry_id?: string | null;
  appraisal_section?: string | null;
  rating?: string | null;
  assigned_to?: string | null;
  due_on?: string | null;
  created_by: string;
  created_by_name?: string | null;
  created_at?: string | null;
};

type FactCheck = {
  id: string;
  claim: string;
  verdict: string;
  confidence: string;
  rationale: string;
  citations: string[];
  contradictory_points: string[];
  verification_steps: string[];
  method: string;
  requested_by_name?: string | null;
  created_at?: string | null;
};

type RoomDetail = {
  room: Room;
  participants: Array<{ user_id: string; name: string; role?: string | null; host: boolean }>;
  evidence: Evidence[];
  appraisal_prompts: Array<{ id: string; label: string; prompt: string }>;
  items: DiscussionItem[];
  factchecks: FactCheck[];
  account: Account;
  privacy_notice: string;
};

type Home = { rooms: Room[]; account: Account };
type FormularyHome = { reviews: ReviewSummary[] };
type ReviewDetail = { entries: Array<{ id: string; title?: string | null; doi?: string | null; extraction?: { study_design?: string | null; sample_size?: number | null } }> };

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function list(items?: unknown[]) {
  return (items ?? []).filter(Boolean).map(String).slice(0, 4).join("; ") || "—";
}

function downloadRecord(room: RoomDetail) {
  const lines: string[] = [
    `# ${room.room.title}`,
    "",
    `Status: ${room.room.status}`,
    `Scheduled: ${room.room.scheduled_at || "not specified"}`,
    `Participants: ${room.participants.map((person) => person.name).join(", ")}`,
    "",
    "## Agenda",
    ...room.room.agenda.map((item) => `- ${item}`),
    "",
    "## Linked evidence",
    ...room.evidence.map((paper) => `- ${paper.title || paper.id}${paper.doi ? ` — DOI: ${paper.doi}` : ""}`),
    "",
    "## Discussion record",
    ...room.items.map((item) => `- **${titleCase(item.kind)}** — ${item.content} _(${item.created_by_name || "Participant"})_`),
    "",
    "## Fact checks",
    ...room.factchecks.map((check) => [
      `### ${check.claim}`,
      `Verdict: **${check.verdict}** · Confidence: ${check.confidence}`,
      check.rationale,
      check.citations.length ? `Sources: ${check.citations.join(", ")}` : "Sources: none",
      "",
    ].join("\n")),
    "",
    "## Scientific boundary",
    "This Journal Club record summarizes collaborative appraisal. Structured extraction and automated fact checks must be verified against original source articles before publication, clinical interpretation or regulatory use.",
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${room.room.title.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "journal-club"}.md`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function FormularyJournalClub() {
  const { user } = useAuth();
  const [home, setHome] = useState<Home | null>(null);
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [reviewEntries, setReviewEntries] = useState<ReviewDetail["entries"]>([]);
  const [selected, setSelected] = useState<RoomDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [form, setForm] = useState({
    title: "",
    review_id: "",
    entry_ids: [] as string[],
    scheduled_at: "",
    meeting_url: "",
    agenda: "",
    appraisal_template: "general",
  });
  const [discussion, setDiscussion] = useState({
    kind: "note",
    content: "",
    entry_id: "",
    assigned_to: "",
    due_on: "",
  });
  const [appraisal, setAppraisal] = useState<Record<string, { content: string; rating: string; entry_id: string }>>({});
  const [claim, setClaim] = useState("");
  const [factEntryIds, setFactEntryIds] = useState<string[]>([]);

  async function loadHome() {
    const [{ data: journal }, { data: formulary }] = await Promise.all([
      api.get<Home>("/api/formulary/journal"),
      api.get<FormularyHome>("/api/formulary"),
    ]);
    setHome(journal);
    setReviews(formulary.reviews);
    return journal;
  }

  async function loadReview(id: string) {
    setForm((current) => ({ ...current, review_id: id, entry_ids: [] }));
    setReviewEntries([]);
    if (!id) return;
    try {
      const { data } = await api.get<ReviewDetail>(`/api/formulary/reviews/${id}`);
      setReviewEntries(data.entries);
    } catch (err: unknown) {
      setError(detail(err));
    }
  }

  async function loadRoom(id: string, quiet = false) {
    if (!quiet) setAction("room");
    try {
      const { data } = await api.get<RoomDetail>(`/api/formulary/journal/rooms/${id}`);
      setSelected(data);
      setFactEntryIds((current) => current.length ? current : data.room.entry_ids);
    } catch (err: unknown) {
      if (!quiet) setError(detail(err));
    } finally {
      if (!quiet) setAction("");
    }
  }

  useEffect(() => {
    loadHome()
      .then((data) => data.rooms[0] ? loadRoom(data.rooms[0].id) : undefined)
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selected || selected.room.status !== "live") return;
    const timer = window.setInterval(() => loadRoom(selected.room.id, true), 8000);
    return () => window.clearInterval(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected?.room.id, selected?.room.status]);

  function toggleEntry(id: string) {
    setForm((current) => ({
      ...current,
      entry_ids: current.entry_ids.includes(id)
        ? current.entry_ids.filter((value) => value !== id)
        : [...current.entry_ids, id],
    }));
  }

  function toggleFactEntry(id: string) {
    setFactEntryIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
  }

  async function createRoom() {
    setAction("create");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<{ room: Room; join_path: string }>("/api/formulary/journal/rooms", {
        title: form.title,
        review_id: form.review_id,
        entry_ids: form.entry_ids,
        scheduled_at: form.scheduled_at ? new Date(form.scheduled_at).toISOString() : null,
        meeting_url: form.meeting_url || null,
        agenda: form.agenda.split("\n").map((line) => line.trim()).filter(Boolean),
        appraisal_template: form.appraisal_template,
      });
      const invite = `${window.location.origin}${data.join_path}`;
      try { await navigator.clipboard.writeText(invite); } catch { /* show it below */ }
      setMessage(`Room created. Private join link copied: ${invite}`);
      setForm({ title: "", review_id: "", entry_ids: [], scheduled_at: "", meeting_url: "", agenda: "", appraisal_template: "general" });
      setReviewEntries([]);
      await loadHome();
      await loadRoom(data.room.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function updateRoom(patch: Partial<Pick<Room, "status" | "locked">>) {
    if (!selected) return;
    setAction("settings");
    setError("");
    try {
      await api.patch(`/api/formulary/journal/rooms/${selected.room.id}`, patch);
      await loadRoom(selected.room.id);
      await loadHome();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function rotateInvite() {
    if (!selected) return;
    setAction("invite");
    setError("");
    try {
      const { data } = await api.post<{ join_path: string }>(`/api/formulary/journal/rooms/${selected.room.id}/invite`);
      const invite = `${window.location.origin}${data.join_path}`;
      try { await navigator.clipboard.writeText(invite); } catch { /* show link in message */ }
      setMessage(`New private join link copied: ${invite}`);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function addDiscussion() {
    if (!selected || !discussion.content.trim()) return;
    setAction("discussion");
    setError("");
    try {
      await api.post(`/api/formulary/journal/rooms/${selected.room.id}/items`, {
        kind: discussion.kind,
        content: discussion.content,
        entry_id: discussion.entry_id || null,
        assigned_to: discussion.kind === "action" ? discussion.assigned_to || null : null,
        due_on: discussion.kind === "action" && discussion.due_on ? discussion.due_on : null,
      });
      setDiscussion({ kind: "note", content: "", entry_id: "", assigned_to: "", due_on: "" });
      await loadRoom(selected.room.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function saveAppraisal(section: string) {
    if (!selected) return;
    const value = appraisal[section];
    if (!value?.content.trim()) return;
    setAction(`appraisal-${section}`);
    setError("");
    try {
      await api.post(`/api/formulary/journal/rooms/${selected.room.id}/items`, {
        kind: "appraisal",
        content: value.content,
        entry_id: value.entry_id || null,
        appraisal_section: section,
        rating: value.rating || "unclear",
      });
      setAppraisal((current) => ({ ...current, [section]: { content: "", rating: "unclear", entry_id: "" } }));
      await loadRoom(selected.room.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  async function runFactCheck() {
    if (!selected || claim.trim().length < 5) return;
    setAction("fact");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<FactCheck>(`/api/formulary/journal/rooms/${selected.room.id}/fact-check`, {
        claim,
        entry_ids: factEntryIds,
      });
      setClaim("");
      setMessage(`Fact check completed: ${data.verdict} (${data.confidence} confidence).`);
      await loadRoom(selected.room.id);
      await loadHome();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setAction("");
    }
  }

  const isHost = selected?.room.owner_user_id === String(user?.id);
  const itemGroups = useMemo(() => {
    const groups: Record<string, DiscussionItem[]> = {};
    for (const item of selected?.items ?? []) {
      (groups[item.kind] ||= []).push(item);
    }
    return groups;
  }, [selected?.items]);

  if (loading && !home) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  if (error && !home) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-900 px-6 py-8 text-white shadow-lg">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary Journal Club Live Room</div>
            <h1 className="mt-3 text-4xl font-bold">Discuss the paper with the evidence table in the room.</h1>
            <p className="mt-4 text-sm leading-7 text-forest-100">
              Run a structured journal club around linked Formulary papers, capture critical appraisal, questions, decisions and actions, and fact-check claims against the room's evidence set.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5 text-sm">
            <div className="grid grid-cols-2 gap-5">
              <div><div className="text-xs text-forest-200">Rooms created</div><div className="mt-1 text-2xl font-bold text-gold-300">{home?.account.journal_room_count ?? 0}</div></div>
              <div><div className="text-xs text-forest-200">Fact checks</div><div className="mt-1 text-2xl font-bold text-gold-300">{home?.account.journal_factcheck_count ?? 0}</div></div>
            </div>
            <div className="mt-3 text-xs text-forest-200">
              {home?.account.is_pro ? "Unlimited with Formulary Scholar" : `Free: ${home?.account.journal_room_limit ?? 0} rooms · ${home?.account.journal_factcheck_limit ?? 0} fact checks`}
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Link className="btn-outline" to="/formulary">← Living Review</Link>
        <Link className="btn-outline" to="/formulary/pkpd">PK/PD Simulator</Link>
        <Link className="btn-outline" to="/formulary/portfolio">Portfolio</Link>
        <Link className="btn-outline" to="/formulary/copilot">Regulatory & Grant Copilot</Link>
      </div>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
        <div className="space-y-6">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Create Journal Club room</h2>
            <div className="mt-4 space-y-3">
              <input className="input" value={form.title} onChange={(e) => setForm((v) => ({ ...v, title: e.target.value }))} placeholder="Room title" />
              <select className="input" value={form.review_id} onChange={(e) => loadReview(e.target.value)}>
                <option value="">Select Living Review</option>
                {reviews.map((review) => <option key={review.id} value={review.id}>{review.title} ({review.paper_count})</option>)}
              </select>
              {!!reviewEntries.length && (
                <div className="max-h-56 space-y-2 overflow-y-auto rounded-2xl border border-gray-100 p-2">
                  {reviewEntries.map((entry) => (
                    <label key={entry.id} className="flex cursor-pointer items-start gap-3 rounded-xl p-3 hover:bg-cream">
                      <input type="checkbox" className="mt-1" checked={form.entry_ids.includes(entry.id)} onChange={() => toggleEntry(entry.id)} />
                      <span>
                        <span className="block text-sm font-semibold">{entry.title || entry.id}</span>
                        <span className="text-xs text-gray-500">{entry.doi || "No DOI"} · {entry.extraction?.study_design || "Design not extracted"} · N={entry.extraction?.sample_size ?? "—"}</span>
                      </span>
                    </label>
                  ))}
                </div>
              )}
              <div className="grid gap-3 sm:grid-cols-2">
                <div><label className="label">Scheduled time</label><input className="input" type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm((v) => ({ ...v, scheduled_at: e.target.value }))} /></div>
                <div>
                  <label className="label">Appraisal template</label>
                  <select className="input" value={form.appraisal_template} onChange={(e) => setForm((v) => ({ ...v, appraisal_template: e.target.value }))}>
                    <option value="general">General critical appraisal</option>
                    <option value="rct">Randomized controlled trial</option>
                    <option value="pk">PK / clinical pharmacology study</option>
                  </select>
                </div>
              </div>
              <input className="input" value={form.meeting_url} onChange={(e) => setForm((v) => ({ ...v, meeting_url: e.target.value }))} placeholder="Optional Zoom / Meet / Teams URL" />
              <textarea className="input min-h-28" value={form.agenda} onChange={(e) => setForm((v) => ({ ...v, agenda: e.target.value }))} placeholder={"Agenda, one item per line\nStudy question\nMethods\nResults\nApplicability"} />
              <button className="btn-primary w-full" disabled={action === "create" || form.title.length < 3 || !form.review_id || !form.entry_ids.length} onClick={createRoom}>
                {action === "create" ? "Creating…" : "Create room & private invite"}
              </button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-bold text-forest-800">Your rooms</h2>
            <div className="mt-4 space-y-2">
              {home?.rooms.length ? home.rooms.map((room) => (
                <button key={room.id} type="button" onClick={() => loadRoom(room.id)} className={`w-full rounded-xl border p-3 text-left ${selected?.room.id === room.id ? "border-forest-500 bg-forest-50" : "border-gray-100 hover:border-forest-200"}`}>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-semibold">{room.title}</span>
                    <StatusBadge status={room.status === "live" ? "active" : room.status === "closed" ? "closed" : "pending"} />
                  </div>
                  <div className="mt-1 text-xs text-gray-500">{room.member_count + 1} participant(s){room.scheduled_at ? ` · ${new Date(room.scheduled_at).toLocaleString()}` : ""}</div>
                </button>
              )) : <p className="text-sm text-gray-400">No Journal Club room yet.</p>}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {selected ? (
            <>
              <div className="card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={selected.room.status === "live" ? "active" : selected.room.status === "closed" ? "closed" : "pending"} />
                      {selected.room.locked && <span className="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">Locked</span>}
                    </div>
                    <h2 className="mt-2 text-2xl font-bold text-gray-900">{selected.room.title}</h2>
                    {selected.room.status === "live" && <p className="mt-2 text-xs font-medium text-forest-600">Live refresh is active every 8 seconds.</p>}
                  </div>
                  <button className="btn-outline text-sm" onClick={() => downloadRecord(selected)}>Export meeting record</button>
                </div>

                {!!selected.room.agenda.length && (
                  <div className="mt-5 rounded-2xl bg-cream p-4">
                    <div className="font-semibold text-forest-800">Agenda</div>
                    <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-600">{selected.room.agenda.map((item) => <li key={item}>{item}</li>)}</ol>
                  </div>
                )}

                <div className="mt-5 flex flex-wrap gap-2">
                  {selected.room.meeting_url && <a className="btn-primary" href={selected.room.meeting_url} target="_blank" rel="noreferrer">Join video call ↗</a>}
                  {isHost && selected.room.status !== "live" && selected.room.status !== "closed" && <button className="btn-primary" disabled={action === "settings"} onClick={() => updateRoom({ status: "live" })}>Start live room</button>}
                  {isHost && selected.room.status === "live" && <button className="btn-outline" disabled={action === "settings"} onClick={() => updateRoom({ status: "closed" })}>Close session</button>}
                  {isHost && <button className="btn-outline" disabled={action === "invite"} onClick={rotateInvite}>New private invite</button>}
                  {isHost && <button className="btn-outline" disabled={action === "settings"} onClick={() => updateRoom({ locked: !selected.room.locked })}>{selected.room.locked ? "Unlock joining" : "Lock joining"}</button>}
                </div>

                <div className="mt-5">
                  <div className="text-sm font-semibold text-forest-800">Participants</div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {selected.participants.map((person) => <span key={person.user_id} className="rounded-full bg-forest-50 px-3 py-1 text-xs text-forest-700">{person.name}{person.host ? " · host" : ""}</span>)}
                  </div>
                </div>
              </div>

              <div className="card">
                <h3 className="text-lg font-bold text-forest-800">Linked evidence table</h3>
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-xs">
                    <thead><tr className="border-b"><th className="p-2">Paper</th><th className="p-2">Design</th><th className="p-2">N</th><th className="p-2">Dose</th><th className="p-2">P-values</th><th className="p-2">Key findings</th></tr></thead>
                    <tbody>
                      {selected.evidence.map((paper) => (
                        <tr key={paper.id} className="border-b border-gray-100 align-top">
                          <td className="p-2"><div className="max-w-xs font-semibold">{paper.title || paper.id}</div><div className="mt-1 text-gray-400">{paper.doi || ""}</div></td>
                          <td className="p-2">{paper.study_design || "—"}</td>
                          <td className="p-2">{paper.sample_size ?? "—"}</td>
                          <td className="p-2">{list(paper.dosing_regimen)}</td>
                          <td className="p-2">{list(paper.p_values)}</td>
                          <td className="p-2">{list(paper.key_findings)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card">
                <h3 className="text-lg font-bold text-forest-800">Critical appraisal</h3>
                <div className="mt-4 space-y-4">
                  {selected.appraisal_prompts.map((prompt) => {
                    const value = appraisal[prompt.id] || { content: "", rating: "unclear", entry_id: "" };
                    const saved = (itemGroups.appraisal || []).filter((item) => item.appraisal_section === prompt.id);
                    return (
                      <div key={prompt.id} className="rounded-2xl border border-gray-100 p-4">
                        <div className="font-semibold text-gray-900">{prompt.label}</div>
                        <p className="mt-1 text-xs leading-5 text-gray-500">{prompt.prompt}</p>
                        {saved.map((item) => <div key={item.id} className="mt-3 rounded-xl bg-cream p-3 text-sm"><span className="font-semibold">{item.rating || "unclear"}:</span> {item.content} <span className="text-xs text-gray-400">— {item.created_by_name}</span></div>)}
                        {selected.room.status !== "closed" && (
                          <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_150px]">
                            <textarea className="input min-h-20" value={value.content} onChange={(e) => setAppraisal((current) => ({ ...current, [prompt.id]: { ...value, content: e.target.value } }))} placeholder="Appraisal note" />
                            <div className="space-y-2">
                              <select className="input" value={value.rating} onChange={(e) => setAppraisal((current) => ({ ...current, [prompt.id]: { ...value, rating: e.target.value } }))}>
                                <option value="strong">Strong</option><option value="adequate">Adequate</option><option value="weak">Weak</option><option value="unclear">Unclear</option>
                              </select>
                              <select className="input" value={value.entry_id} onChange={(e) => setAppraisal((current) => ({ ...current, [prompt.id]: { ...value, entry_id: e.target.value } }))}>
                                <option value="">Whole room</option>
                                {selected.evidence.map((paper) => <option key={paper.id} value={paper.id}>{paper.title || paper.id}</option>)}
                              </select>
                              <button className="btn-outline w-full text-xs" disabled={action === `appraisal-${prompt.id}` || !value.content.trim()} onClick={() => saveAppraisal(prompt.id)}>Save</button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {selected.room.status !== "closed" && (
                <div className="card">
                  <h3 className="text-lg font-bold text-forest-800">Discussion record</h3>
                  <div className="mt-4 space-y-3">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <select className="input" value={discussion.kind} onChange={(e) => setDiscussion((v) => ({ ...v, kind: e.target.value }))}>
                        <option value="note">Note</option><option value="question">Question</option><option value="claim">Claim</option><option value="decision">Decision</option><option value="action">Action item</option>
                      </select>
                      <select className="input" value={discussion.entry_id} onChange={(e) => setDiscussion((v) => ({ ...v, entry_id: e.target.value }))}>
                        <option value="">Whole discussion</option>
                        {selected.evidence.map((paper) => <option key={paper.id} value={paper.id}>{paper.title || paper.id}</option>)}
                      </select>
                    </div>
                    <textarea className="input min-h-24" value={discussion.content} onChange={(e) => setDiscussion((v) => ({ ...v, content: e.target.value }))} placeholder="Add a question, observation, decision or action…" />
                    {discussion.kind === "action" && <div className="grid gap-3 sm:grid-cols-2"><input className="input" value={discussion.assigned_to} onChange={(e) => setDiscussion((v) => ({ ...v, assigned_to: e.target.value }))} placeholder="Assigned to" /><input className="input" type="date" value={discussion.due_on} onChange={(e) => setDiscussion((v) => ({ ...v, due_on: e.target.value }))} /></div>}
                    <button className="btn-primary" disabled={action === "discussion" || !discussion.content.trim()} onClick={addDiscussion}>Add to room record</button>
                  </div>
                  <div className="mt-6 space-y-2">
                    {selected.items.filter((item) => item.kind !== "appraisal").map((item) => (
                      <div key={item.id} className="rounded-xl border border-gray-100 p-3 text-sm">
                        <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-bold uppercase">{item.kind}</span><span className="text-xs text-gray-400">{item.created_by_name}{item.created_at ? ` · ${new Date(item.created_at).toLocaleTimeString()}` : ""}</span></div>
                        <p className="mt-2 text-gray-700">{item.content}</p>
                        {item.assigned_to && <div className="mt-2 text-xs text-forest-700">Assigned: {item.assigned_to}{item.due_on ? ` · due ${item.due_on}` : ""}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="card border border-gold-200">
                <h3 className="text-lg font-bold text-forest-800">Evidence-grounded fact check</h3>
                <p className="mt-2 text-sm text-gray-500">Checks only the papers linked to this room. It does not search model memory for unsupported evidence.</p>
                <textarea className="input mt-4 min-h-24" value={claim} onChange={(e) => setClaim(e.target.value)} placeholder="Claim to test, e.g. The intervention significantly improved the primary endpoint without increasing serious adverse events." />
                <div className="mt-3 flex flex-wrap gap-2">
                  {selected.evidence.map((paper) => <label key={paper.id} className="flex items-center gap-1 rounded-full bg-cream px-3 py-1 text-xs"><input type="checkbox" checked={factEntryIds.includes(paper.id)} onChange={() => toggleFactEntry(paper.id)} /> {paper.title || paper.id}</label>)}
                </div>
                <button className="btn-primary mt-4" disabled={action === "fact" || claim.trim().length < 5 || !factEntryIds.length} onClick={runFactCheck}>{action === "fact" ? "Checking…" : "Fact-check against linked evidence"}</button>

                <div className="mt-6 space-y-4">
                  {selected.factchecks.map((check) => (
                    <article key={check.id} className="rounded-2xl border border-gray-100 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="font-semibold text-gray-900">{check.claim}</div>
                        <div className="flex gap-2"><span className="rounded-full bg-forest-50 px-2 py-1 text-xs font-semibold text-forest-700">{check.verdict}</span><span className="rounded-full bg-gray-100 px-2 py-1 text-xs">{check.confidence}</span></div>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-gray-600">{check.rationale}</p>
                      {!!check.citations.length && <div className="mt-3 text-xs text-forest-700">Evidence: {check.citations.join(", ")}</div>}
                      {!!check.contradictory_points.length && <div className="mt-3 text-xs text-red-700">Counterpoints: {check.contradictory_points.join(" · ")}</div>}
                      {!!check.verification_steps.length && <div className="mt-3 text-xs text-gray-500">Verify: {check.verification_steps.join(" · ")}</div>}
                      <div className="mt-2 text-[10px] text-gray-400">{check.requested_by_name} · {check.method}</div>
                    </article>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
                <strong>Room privacy & research boundary:</strong> {selected.privacy_notice} Fact checks use structured extractions that may themselves require correction, so important claims must still be checked against the original article.
              </div>
            </>
          ) : <div className="card py-20 text-center text-gray-400">Create or select a Journal Club room.</div>}
        </div>
      </section>
    </div>
  );
}
