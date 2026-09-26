import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge } from "../components/Layout";

type Account = {
  plan: string;
  is_pro: boolean;
  review_count: number;
  paper_count: number;
  review_limit: number | null;
  paper_limit: number | null;
  upgrade_path: string;
};

type ReviewSummary = {
  id: string;
  title: string;
  research_question: string;
  status: string;
  paper_count: number;
  updated_at?: string;
};

type Extraction = {
  article_title?: string | null;
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
  pk_parameters?: {
    auc?: string[];
    cmax?: string[];
    tmax?: string[];
    half_life?: string[];
    clearance?: string[];
    volume_of_distribution?: string[];
    bioavailability?: string[];
  };
  key_findings?: string[];
  limitations?: string[];
  evidence_spans?: { field?: string; page?: number | null; snippet?: string }[];
  [key: string]: unknown;
};

type Entry = {
  id: string;
  review_id: string;
  source_type: string;
  doi?: string | null;
  title?: string | null;
  journal?: string | null;
  authors?: string[];
  published?: string | null;
  openalex_id?: string | null;
  cited_by_count: number;
  extraction: Extraction;
  extraction_method?: string;
  corrections?: Array<{ field_path: string; corrected_at?: string }>;
  citation_watch?: Array<{
    openalex_id?: string;
    doi?: string;
    title?: string;
    published?: string;
    journal?: string;
    cited_by_count?: number;
  }>;
  citation_watch_last_checked?: string | null;
};

type Home = {
  product: string;
  tagline: string;
  account: Account;
  reviews: ReviewSummary[];
  mvp: { features: string[]; coming_next: string[] };
};

type Detail = {
  review: {
    id: string;
    title: string;
    research_question: string;
    inclusion_criteria?: string | null;
    exclusion_criteria?: string | null;
    consent_to_model_improvement: boolean;
    status: string;
  };
  entries: Entry[];
  account: Account;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

function compact(items?: unknown[]) {
  return (items ?? []).filter(Boolean).map(String).slice(0, 3).join("; ") || "—";
}

function downloadCsv(reviewTitle: string, entries: Entry[]) {
  const headers = [
    "Title", "DOI", "Journal", "Published", "Study design", "Sample size",
    "Dose", "P values", "AUC", "Cmax", "Half-life", "Adverse events", "Citations"
  ];
  const rows = entries.map((entry) => [
    entry.title ?? "",
    entry.doi ?? "",
    entry.journal ?? "",
    entry.published ?? "",
    entry.extraction.study_design ?? "",
    entry.extraction.sample_size ?? "",
    compact(entry.extraction.dosing_regimen),
    compact(entry.extraction.p_values),
    compact(entry.extraction.pk_parameters?.auc),
    compact(entry.extraction.pk_parameters?.cmax),
    compact(entry.extraction.pk_parameters?.half_life),
    compact(entry.extraction.adverse_events),
    entry.cited_by_count ?? 0,
  ]);
  const quote = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(quote).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = `${reviewTitle.replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "formulary-review"}.csv`;
  link.click();
  URL.revokeObjectURL(href);
}

export default function Formulary() {
  const [home, setHome] = useState<Home | null>(null);
  const [detailData, setDetailData] = useState<Detail | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [doi, setDoi] = useState("");
  const [pdfDoi, setPdfDoi] = useState("");
  const [pdf, setPdf] = useState<File | null>(null);
  const [newReview, setNewReview] = useState({
    title: "",
    research_question: "",
    inclusion_criteria: "",
    exclusion_criteria: "",
    consent_to_model_improvement: false,
  });
  const [correction, setCorrection] = useState({
    entry_id: "",
    field_path: "sample_size",
    value: "",
    note: "",
  });

  async function loadHome(selectFirst = false) {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.get<Home>("/api/formulary");
      setHome(data);
      if (selectFirst && data.reviews[0]) {
        await loadReview(data.reviews[0].id);
      }
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadReview(id: string) {
    setSelectedId(id);
    setActionLoading("review");
    setError("");
    try {
      const { data } = await api.get<Detail>(`/api/formulary/reviews/${id}`);
      setDetailData(data);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  useEffect(() => {
    loadHome(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createReview() {
    setActionLoading("create");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<{ id: string }>("/api/formulary/reviews", newReview);
      setNewReview({
        title: "",
        research_question: "",
        inclusion_criteria: "",
        exclusion_criteria: "",
        consent_to_model_improvement: false,
      });
      setMessage("Living literature review created.");
      await loadHome();
      await loadReview(data.id);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  async function addDoi() {
    if (!selectedId || !doi.trim()) return;
    setActionLoading("doi");
    setError("");
    setMessage("");
    try {
      await api.post(`/api/formulary/reviews/${selectedId}/doi`, { doi });
      setDoi("");
      setMessage("Paper added and structured extraction completed.");
      await loadReview(selectedId);
      await loadHome();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  async function uploadPdf() {
    if (!selectedId || !pdf) return;
    setActionLoading("pdf");
    setError("");
    setMessage("");
    const form = new FormData();
    form.append("file", pdf);
    if (pdfDoi.trim()) form.append("doi", pdfDoi.trim());
    try {
      await api.post(`/api/formulary/reviews/${selectedId}/pdf`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPdf(null);
      setPdfDoi("");
      setMessage("PDF extracted into the living evidence table.");
      await loadReview(selectedId);
      await loadHome();
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  async function refreshCitations(entryId?: string) {
    if (!selectedId) return;
    setActionLoading(entryId ? `cite-${entryId}` : "citations");
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<{ entries_refreshed: number; new_citations: number }>(
        `/api/formulary/reviews/${selectedId}/refresh-citations`,
        { entry_id: entryId || undefined },
      );
      setMessage(`Citation watch refreshed for ${data.entries_refreshed} paper(s); ${data.new_citations} newly surfaced citation(s).`);
      await loadReview(selectedId);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  async function applyCorrection() {
    if (!correction.entry_id || !correction.field_path || !correction.value) return;
    setActionLoading("correction");
    setError("");
    setMessage("");
    let value: unknown = correction.value;
    if (correction.field_path === "sample_size" && /^\d+$/.test(correction.value.trim())) {
      value = Number(correction.value);
    } else if (correction.value.trim().startsWith("[") || correction.value.trim().startsWith("{")) {
      try { value = JSON.parse(correction.value); } catch { /* keep as text */ }
    }
    try {
      await api.patch(`/api/formulary/entries/${correction.entry_id}`, {
        field_path: correction.field_path,
        value,
        note: correction.note || undefined,
      });
      setCorrection({ entry_id: "", field_path: "sample_size", value: "", note: "" });
      setMessage("Correction saved with provenance.");
      await loadReview(selectedId);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setActionLoading("");
    }
  }

  const entries = detailData?.entries ?? [];
  const selectedSummary = useMemo(
    () => home?.reviews.find((review) => review.id === selectedId),
    [home, selectedId],
  );

  if (loading && !home) {
    return <div className="flex h-64 items-center justify-center"><Spinner /></div>;
  }
  if (error && !home) return <PageError message={error} />;

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-3xl bg-forest-900 text-white shadow-lg">
        <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1.2fr_0.8fr] lg:px-9">
          <div>
            <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary · Living Literature Review MVP</div>
            <h1 className="mt-3 text-4xl font-bold">The operating system for translational pharmaceutical science.</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-forest-100">
              Turn DOI metadata and uploaded papers into a structured pharmaceutical evidence table with study design,
              sample size, dosing, p-values, adverse events and PK parameters—then keep the evidence alive as new citations appear.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 text-xs">
              {home?.mvp.features.map((item) => (
                <span key={item} className="rounded-full border border-forest-600 px-3 py-1.5">✓ {item}</span>
              ))}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/10 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="text-xs text-forest-200">Current plan</div>
                <div className="mt-1 text-xl font-bold text-gold-300">{home?.account.is_pro ? "Formulary Scholar" : "Free Researcher"}</div>
              </div>
              <StatusBadge status={home?.account.is_pro ? "active" : "draft"} />
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl bg-forest-950/40 p-3"><div className="text-xs text-forest-300">Reviews</div><div className="mt-1 font-bold">{home?.account.review_count}{home?.account.review_limit ? ` / ${home.account.review_limit}` : ""}</div></div>
              <div className="rounded-xl bg-forest-950/40 p-3"><div className="text-xs text-forest-300">Papers</div><div className="mt-1 font-bold">{home?.account.paper_count}{home?.account.paper_limit ? ` / ${home.account.paper_limit}` : ""}</div></div>
            </div>
            {!home?.account.is_pro && <Link to="/pricing" className="mt-5 block rounded-xl bg-gold-400 px-4 py-3 text-center text-sm font-bold text-forest-900">Upgrade to Formulary Scholar</Link>}
          </div>
        </div>
      </section>

      {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm font-medium text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
        <div className="space-y-5">
          <div className="card">
            <h2 className="text-xl font-bold text-forest-800">Create a living review</h2>
            <div className="mt-4 space-y-3">
              <input className="input" placeholder="Review title" value={newReview.title} onChange={(e) => setNewReview((v) => ({ ...v, title: e.target.value }))} />
              <textarea className="input min-h-24" placeholder="Research question / PICO" value={newReview.research_question} onChange={(e) => setNewReview((v) => ({ ...v, research_question: e.target.value }))} />
              <textarea className="input min-h-20" placeholder="Inclusion criteria, optional" value={newReview.inclusion_criteria} onChange={(e) => setNewReview((v) => ({ ...v, inclusion_criteria: e.target.value }))} />
              <textarea className="input min-h-20" placeholder="Exclusion criteria, optional" value={newReview.exclusion_criteria} onChange={(e) => setNewReview((v) => ({ ...v, exclusion_criteria: e.target.value }))} />
              <label className="flex items-start gap-3 rounded-xl bg-cream p-3 text-xs text-gray-600">
                <input type="checkbox" checked={newReview.consent_to_model_improvement} onChange={(e) => setNewReview((v) => ({ ...v, consent_to_model_improvement: e.target.checked }))} />
                <span>Allow de-identified corrections from this review to be considered for future model improvement. This is optional and off by default.</span>
              </label>
              <button className="btn-primary w-full" disabled={actionLoading === "create" || newReview.title.length < 3 || newReview.research_question.length < 3} onClick={createReview}>
                {actionLoading === "create" ? "Creating…" : "Create review"}
              </button>
            </div>
          </div>

          <div className="card">
            <h2 className="text-lg font-bold text-forest-800">Your reviews</h2>
            <div className="mt-4 space-y-2">
              {home?.reviews.length ? home.reviews.map((review) => (
                <button key={review.id} type="button" onClick={() => loadReview(review.id)} className={`w-full rounded-xl border p-3 text-left transition ${selectedId === review.id ? "border-forest-500 bg-forest-50" : "border-gray-100 hover:border-forest-200"}`}>
                  <div className="font-semibold text-gray-900">{review.title}</div>
                  <div className="mt-1 text-xs text-gray-500">{review.paper_count} paper(s) · {review.research_question}</div>
                </button>
              )) : <div className="text-sm text-gray-400">No living review yet.</div>}
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {!selectedId ? (
            <div className="card py-16 text-center text-gray-400">Create or select a review to begin building the evidence table.</div>
          ) : (
            <>
              <div className="card">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wide text-forest-500">Active review</div>
                    <h2 className="mt-1 text-2xl font-bold text-gray-900">{detailData?.review.title ?? selectedSummary?.title}</h2>
                    <p className="mt-2 text-sm text-gray-600">{detailData?.review.research_question}</p>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-outline text-sm" disabled={actionLoading === "citations"} onClick={() => refreshCitations()}>
                      {actionLoading === "citations" ? "Refreshing…" : "Refresh citations"}
                    </button>
                    <button className="btn-outline text-sm" disabled={!entries.length} onClick={() => downloadCsv(detailData?.review.title ?? "Formulary Review", entries)}>Export CSV</button>
                  </div>
                </div>

                <div className="mt-6 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl bg-cream p-4">
                    <div className="font-semibold text-forest-800">Add by DOI</div>
                    <p className="mt-1 text-xs text-gray-500">Pull bibliographic metadata and available abstract evidence, then structure it for pharmaceutical review.</p>
                    <div className="mt-3 flex gap-2">
                      <input className="input flex-1" placeholder="10.xxxx/..." value={doi} onChange={(e) => setDoi(e.target.value)} />
                      <button className="btn-primary shrink-0" disabled={actionLoading === "doi"} onClick={addDoi}>{actionLoading === "doi" ? "Adding…" : "Add DOI"}</button>
                    </div>
                  </div>

                  <div className="rounded-2xl bg-cream p-4">
                    <div className="font-semibold text-forest-800">Upload article PDF</div>
                    <p className="mt-1 text-xs text-gray-500">Extract study-level and PK/PD fields from a PDF you are authorized to use.</p>
                    <div className="mt-3 space-y-2">
                      <input className="input" type="file" accept="application/pdf,.pdf" onChange={(e) => setPdf(e.target.files?.[0] ?? null)} />
                      <input className="input" placeholder="Optional DOI for citation tracking" value={pdfDoi} onChange={(e) => setPdfDoi(e.target.value)} />
                      <button className="btn-primary w-full" disabled={!pdf || actionLoading === "pdf"} onClick={uploadPdf}>{actionLoading === "pdf" ? "Extracting…" : "Extract PDF"}</button>
                    </div>
                  </div>
                </div>
              </div>

              <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
                <div className="overflow-x-auto">
                  <table className="min-w-[1200px] w-full text-left text-xs">
                    <thead className="bg-forest-50 text-forest-800">
                      <tr>
                        {["Paper", "Design", "N", "Dose", "P-values", "AUC", "Cmax", "t½", "Adverse events", "Citations", "Actions"].map((label) => <th key={label} className="px-3 py-3 font-semibold">{label}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map((entry) => (
                        <tr key={entry.id} className="border-t border-gray-100 align-top">
                          <td className="max-w-72 px-3 py-4">
                            <div className="font-semibold text-gray-900">{entry.title || "Untitled article"}</div>
                            <div className="mt-1 text-[11px] text-gray-400">{entry.doi || entry.source_type} · {entry.journal || "Journal unavailable"}</div>
                            <div className="mt-1 text-[10px] text-gray-400">{entry.extraction_method}</div>
                          </td>
                          <td className="px-3 py-4">{entry.extraction.study_design || "—"}</td>
                          <td className="px-3 py-4">{entry.extraction.sample_size ?? "—"}</td>
                          <td className="max-w-44 px-3 py-4">{compact(entry.extraction.dosing_regimen)}</td>
                          <td className="max-w-44 px-3 py-4">{compact(entry.extraction.p_values)}</td>
                          <td className="max-w-40 px-3 py-4">{compact(entry.extraction.pk_parameters?.auc)}</td>
                          <td className="max-w-40 px-3 py-4">{compact(entry.extraction.pk_parameters?.cmax)}</td>
                          <td className="max-w-40 px-3 py-4">{compact(entry.extraction.pk_parameters?.half_life)}</td>
                          <td className="max-w-56 px-3 py-4">{compact(entry.extraction.adverse_events)}</td>
                          <td className="px-3 py-4">
                            <div className="font-semibold">{entry.cited_by_count ?? 0}</div>
                            <div className="mt-1 text-[10px] text-gray-400">{entry.citation_watch?.length ?? 0} recent surfaced</div>
                          </td>
                          <td className="px-3 py-4">
                            <div className="space-y-2">
                              <button className="text-forest-700 underline" disabled={actionLoading === `cite-${entry.id}`} onClick={() => refreshCitations(entry.id)}>
                                {actionLoading === `cite-${entry.id}` ? "Refreshing…" : "Refresh"}
                              </button>
                              <button className="block text-forest-700 underline" onClick={() => setCorrection((v) => ({ ...v, entry_id: entry.id }))}>Correct field</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                      {!entries.length && <tr><td colSpan={11} className="px-4 py-12 text-center text-sm text-gray-400">No papers yet. Add a DOI or upload a PDF.</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>

              {correction.entry_id && (
                <div className="card border border-gold-200">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="text-lg font-bold text-forest-800">Correct extracted evidence</h3>
                      <p className="mt-1 text-xs text-gray-500">Your correction is stored with old value, new value, author and timestamp.</p>
                    </div>
                    <button className="text-xl text-gray-400" onClick={() => setCorrection({ entry_id: "", field_path: "sample_size", value: "", note: "" })}>×</button>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <select className="input" value={correction.field_path} onChange={(e) => setCorrection((v) => ({ ...v, field_path: e.target.value }))}>
                      <option value="sample_size">Sample size</option>
                      <option value="study_design">Study design</option>
                      <option value="population">Population</option>
                      <option value="intervention">Intervention</option>
                      <option value="comparator">Comparator</option>
                      <option value="dosing_regimen">Dosing regimen</option>
                      <option value="p_values">P-values</option>
                      <option value="adverse_events">Adverse events</option>
                      <option value="pk_parameters.auc">PK: AUC</option>
                      <option value="pk_parameters.cmax">PK: Cmax</option>
                      <option value="pk_parameters.half_life">PK: half-life</option>
                    </select>
                    <input className="input md:col-span-2" placeholder='Correct value; arrays can be JSON like ["5 mg","10 mg"]' value={correction.value} onChange={(e) => setCorrection((v) => ({ ...v, value: e.target.value }))} />
                    <button className="btn-primary" disabled={actionLoading === "correction"} onClick={applyCorrection}>{actionLoading === "correction" ? "Saving…" : "Save correction"}</button>
                    <input className="input md:col-span-4" placeholder="Correction note / verification source, optional" value={correction.note} onChange={(e) => setCorrection((v) => ({ ...v, note: e.target.value }))} />
                  </div>
                </div>
              )}

              {entries.some((entry) => (entry.citation_watch?.length ?? 0) > 0) && (
                <div className="card">
                  <h3 className="text-xl font-bold text-forest-800">Newer papers citing your evidence base</h3>
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    {entries.flatMap((entry) => entry.citation_watch ?? []).slice(0, 12).map((citation, index) => (
                      <div key={citation.openalex_id ?? index} className="rounded-xl border border-gray-100 p-4">
                        <div className="font-semibold text-gray-900">{citation.title}</div>
                        <div className="mt-1 text-xs text-gray-500">{citation.published || "Date unavailable"} · {citation.journal || "Source unavailable"}</div>
                        {citation.doi && <div className="mt-2 text-xs text-forest-700">{citation.doi}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
        <strong>Research integrity:</strong> Formulary extracts and organizes evidence; it does not certify that a paper is correct. Verify extracted values against the source before publication, clinical use, regulatory submission or grant submission.
      </section>

      <section>
        <h2 className="text-xl font-bold text-forest-800">Formulary roadmap</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {home?.mvp.coming_next.map((item) => <div key={item} className="card text-sm font-semibold text-gray-700">{item}</div>)}
        </div>
      </section>
    </div>
  );
}
