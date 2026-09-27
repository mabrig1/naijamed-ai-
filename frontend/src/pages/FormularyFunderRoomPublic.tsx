import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, ProgressBar, Spinner } from "../components/Layout";

type Snapshot = {
  project?: Record<string, any>;
  profile?: Record<string, any>;
  partners?: Array<Record<string, any>>;
  work_packages?: Array<Record<string, any>>;
  milestones?: Array<Record<string, any>>;
  readiness?: {
    score: number;
    dimensions: Array<{
      key: string;
      label: string;
      weight: number;
      earned: number;
      completion: number;
      status: "strong" | "developing" | "gap";
      guidance: string;
    }>;
    lens?: {
      label?: string;
      verified_on?: string;
      sources?: Array<{ organization: string; label: string; url: string; criteria: string[] }>;
      notice?: string;
    };
    notice?: string;
  };
  privacy_notice?: string;
};

type Payload = {
  room: {
    id: string;
    recipient_label?: string | null;
    note?: string | null;
    expires_at: string;
    created_at?: string | null;
  };
  snapshot: Snapshot;
  access_notice: string;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "This funder room is unavailable.";
}

function money(amount?: number | null, currency = "NGN") {
  if (amount == null) return "Not disclosed";
  try {
    return new Intl.NumberFormat("en-NG", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${currency} ${new Intl.NumberFormat("en-NG").format(amount)}`;
  }
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

function paragraph(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

export default function FormularyFunderRoomPublic() {
  const { token = "" } = useParams();
  const [payload, setPayload] = useState<Payload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<Payload>(`/api/formulary/funder-room/${encodeURIComponent(token)}`)
      .then(({ data }) => setPayload(data))
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => setLoading(false));
  }, [token]);

  const p = payload?.snapshot.project ?? {};
  const profile = payload?.snapshot.profile ?? {};
  const partners = payload?.snapshot.partners ?? [];
  const workPackages = payload?.snapshot.work_packages ?? [];
  const milestones = payload?.snapshot.milestones ?? [];
  const readiness = payload?.snapshot.readiness;

  const statCards = useMemo(() => [
    ["Duration", p.duration_months ? `${p.duration_months} months` : "Not stated"],
    ["Budget", money(p.budget_amount, p.budget_currency || "NGN")],
    ["Consortium", partners.length ? `${partners.length} partner(s)` : "Not disclosed"],
    ["Work packages", workPackages.length ? String(workPackages.length) : "Not disclosed"],
  ], [p.duration_months, p.budget_amount, p.budget_currency, partners.length, workPackages.length]);

  if (loading) return <div className="flex min-h-screen items-center justify-center bg-cream"><Spinner /></div>;
  if (error || !payload) return <div className="mx-auto max-w-3xl py-20"><PageError message={error || "Funder room unavailable."} /></div>;

  const sections = [
    ["Innovation / conceptual advance", paragraph(profile.innovation_case)],
    ["Global relevance", paragraph(profile.global_relevance)],
    ["Rigor & feasibility", paragraph(profile.rigor_feasibility)],
    ["Impact pathway", paragraph(profile.impact_pathway)],
    ["Institutional capacity & research environment", paragraph(profile.institutional_capacity)],
    ["Ethics & governance", paragraph(profile.ethics_governance)],
    ["Data, reproducibility & open science", paragraph(profile.data_open_science)],
    ["Equity, capacity building & research culture", paragraph(profile.equity_capacity_building)],
    ["Sustainability & scale", paragraph(profile.sustainability_scale)],
    ["Policy / implementation translation", paragraph(profile.policy_translation)],
    ["Monitoring & evaluation", paragraph(profile.monitoring_evaluation)],
    ["Risk management", paragraph(profile.risk_management)],
    ["Leverage & additionality", paragraph(profile.cofunding_leverage)],
  ].filter(([, value]) => Boolean(value)) as Array<[string, string]>;

  return (
    <div className="min-h-screen bg-cream text-gray-900">
      <header className="border-b border-forest-800 bg-forest-950 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4 sm:px-7">
          <div>
            <div className="text-sm font-bold text-gold-300">NigerFlora BioSciences · Formulary</div>
            <div className="text-xs text-forest-200">Controlled Funder Due-Diligence Room</div>
          </div>
          <div className="rounded-full border border-white/10 bg-white/10 px-3 py-1.5 text-xs">
            Expires {new Date(payload.room.expires_at).toLocaleDateString()}
          </div>
        </div>
      </header>

      <main>
        <section className="bg-forest-900 text-white">
          <div className="mx-auto max-w-7xl px-5 py-14 sm:px-7 lg:py-20">
            <div className="max-w-5xl">
              <div className="inline-flex rounded-full bg-gold-300/15 px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] text-gold-300">
                {p.acronym || "International research programme"}
              </div>
              <h1 className="mt-5 text-4xl font-bold leading-tight md:text-6xl">{p.title || "Research programme"}</h1>
              <p className="mt-5 max-w-4xl text-base leading-8 text-forest-100 md:text-lg">{p.summary || "Project summary not provided."}</p>

              <div className="mt-8 flex flex-wrap gap-3 text-sm">
                {p.host_institution && <span className="rounded-full border border-white/10 bg-white/10 px-4 py-2">{p.host_institution}</span>}
                {p.location && <span className="rounded-full border border-white/10 bg-white/10 px-4 py-2">{p.location}</span>}
                {p.funder_name && <span className="rounded-full border border-gold-300/30 bg-gold-300/10 px-4 py-2 text-gold-200">{p.funder_name}</span>}
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-7xl space-y-8 px-5 py-10 sm:px-7">
          {payload.room.note && (
            <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
              <strong>Shared context:</strong> {payload.room.note}
            </section>
          )}

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {statCards.map(([label, value]) => (
              <article key={label} className="rounded-2xl border border-forest-100 bg-white p-5 shadow-sm">
                <div className="text-xs font-bold uppercase tracking-wide text-forest-500">{label}</div>
                <div className="mt-2 text-xl font-bold text-forest-900">{value}</div>
              </article>
            ))}
          </section>

          <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
            <div className="space-y-6">
              {p.problem_statement && (
                <article className="card">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-forest-500">The challenge</div>
                  <h2 className="mt-2 text-2xl font-bold text-forest-900">Why this research matters</h2>
                  <p className="mt-4 whitespace-pre-line text-sm leading-7 text-gray-650">{p.problem_statement}</p>
                </article>
              )}

              {!!p.objectives?.length && (
                <article className="card">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-forest-500">Scientific direction</div>
                  <h2 className="mt-2 text-2xl font-bold text-forest-900">Specific objectives</h2>
                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {p.objectives.map((objective: string, index: number) => (
                      <div key={objective} className="rounded-2xl bg-cream p-4 text-sm leading-6">
                        <span className="mr-2 font-bold text-forest-700">{String(index + 1).padStart(2, "0")}.</span>{objective}
                      </div>
                    ))}
                  </div>
                </article>
              )}

              {!!sections.length && (
                <article className="card">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-forest-500">Investment case</div>
                  <h2 className="mt-2 text-2xl font-bold text-forest-900">Why this programme is worth backing</h2>
                  <div className="mt-5 space-y-5">
                    {sections.map(([label, value]) => (
                      <div key={label} className="border-l-2 border-gold-300 pl-4">
                        <h3 className="font-bold text-gray-900">{label}</h3>
                        <p className="mt-2 whitespace-pre-line text-sm leading-7 text-gray-600">{value}</p>
                      </div>
                    ))}
                  </div>
                </article>
              )}

              {!!workPackages.length && (
                <article className="card">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-forest-500">Delivery architecture</div>
                  <h2 className="mt-2 text-2xl font-bold text-forest-900">Work packages</h2>
                  <div className="mt-5 space-y-3">
                    {workPackages.map((wp) => (
                      <div key={`${wp.sequence}-${wp.title}`} className="rounded-2xl border border-gray-100 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="font-bold text-forest-900">WP{wp.sequence}: {wp.title}</div>
                          {wp.budget_amount != null && <div className="text-sm font-semibold text-forest-700">{money(wp.budget_amount, p.budget_currency || "NGN")}</div>}
                        </div>
                        {wp.lead_partner && <div className="mt-1 text-xs text-gray-500">Lead: {wp.lead_partner}</div>}
                        {wp.objective && <p className="mt-3 text-sm leading-6 text-gray-600">{wp.objective}</p>}
                        {!!wp.outputs?.length && <div className="mt-3 flex flex-wrap gap-2">{wp.outputs.map((output: string) => <span key={output} className="rounded-full bg-forest-50 px-3 py-1 text-xs text-forest-700">{output}</span>)}</div>}
                      </div>
                    ))}
                  </div>
                </article>
              )}

              {!!partners.length && (
                <article className="card">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-forest-500">Consortium</div>
                  <h2 className="mt-2 text-2xl font-bold text-forest-900">Complementary delivery partners</h2>
                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {partners.map((partner) => (
                      <div key={`${partner.organization}-${partner.country}`} className="rounded-2xl bg-cream p-4">
                        <div className="font-bold text-gray-900">{partner.organization}</div>
                        <div className="mt-1 text-xs text-gray-500">{partner.country || "Country not disclosed"} · {titleCase(partner.partner_type || "partner")} · {titleCase(partner.status || "prospect")}</div>
                        {partner.proposed_role && <p className="mt-3 text-sm leading-6 text-gray-600">{partner.proposed_role}</p>}
                      </div>
                    ))}
                  </div>
                </article>
              )}
            </div>

            <aside className="space-y-6">
              {readiness && (
                <section className="card border border-gold-200">
                  <div className="text-xs font-bold uppercase tracking-[0.18em] text-gold-700">Funder preparation lens</div>
                  <div className="mt-3 flex items-end justify-between gap-3">
                    <div>
                      <div className="text-4xl font-bold text-forest-900">{readiness.score}%</div>
                      <div className="mt-1 text-xs text-gray-500">dossier completeness</div>
                    </div>
                    <div className="max-w-40 text-right text-xs text-gray-500">{readiness.lens?.label}</div>
                  </div>
                  <div className="mt-4"><ProgressBar value={readiness.score} /></div>
                  <p className="mt-3 text-xs leading-5 text-gray-500">{readiness.notice}</p>

                  <div className="mt-5 space-y-3">
                    {readiness.dimensions.map((dimension) => (
                      <div key={dimension.key}>
                        <div className="flex items-center justify-between gap-3 text-xs">
                          <span className="font-semibold text-gray-700">{dimension.label}</span>
                          <span>{dimension.completion}%</span>
                        </div>
                        <div className="mt-1"><ProgressBar value={dimension.completion} /></div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {!!profile.impact_metrics?.length && (
                <section className="card">
                  <h2 className="text-lg font-bold text-forest-900">Measurable impact</h2>
                  <ul className="mt-4 space-y-3 text-sm leading-6 text-gray-600">
                    {profile.impact_metrics.map((item: string) => <li key={item} className="flex gap-2"><span className="text-forest-600">✓</span><span>{item}</span></li>)}
                  </ul>
                </section>
              )}

              {!!profile.capacity_outputs?.length && (
                <section className="card">
                  <h2 className="text-lg font-bold text-forest-900">Capacity that remains</h2>
                  <ul className="mt-4 space-y-3 text-sm leading-6 text-gray-600">
                    {profile.capacity_outputs.map((item: string) => <li key={item} className="flex gap-2"><span className="text-gold-600">◆</span><span>{item}</span></li>)}
                  </ul>
                </section>
              )}

              {!!profile.sdg_alignment?.length && (
                <section className="card">
                  <h2 className="text-lg font-bold text-forest-900">Global development alignment</h2>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {profile.sdg_alignment.map((item: string) => <span key={item} className="rounded-full bg-forest-50 px-3 py-1.5 text-xs font-semibold text-forest-700">{item}</span>)}
                  </div>
                </section>
              )}

              {!!milestones.length && (
                <section className="card">
                  <h2 className="text-lg font-bold text-forest-900">Critical path</h2>
                  <div className="mt-4 space-y-3">
                    {milestones.slice(0, 8).map((milestone) => (
                      <div key={`${milestone.title}-${milestone.due_on}`} className="rounded-xl bg-cream p-3">
                        <div className="text-sm font-semibold">{milestone.title}</div>
                        <div className="mt-1 text-xs text-gray-500">{milestone.due_on || "Date not disclosed"} · {titleCase(milestone.status || "planned")}</div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {readiness?.lens?.sources?.length ? (
                <section className="card">
                  <h2 className="text-lg font-bold text-forest-900">Preparation criteria references</h2>
                  <div className="mt-4 space-y-2">
                    {readiness.lens.sources.map((source) => (
                      <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="block rounded-xl border border-gray-100 p-3 text-sm hover:border-forest-200">
                        <div className="font-semibold">{source.organization}</div>
                        <div className="mt-1 text-xs text-gray-500">{source.label}</div>
                      </a>
                    ))}
                  </div>
                </section>
              ) : null}
            </aside>
          </section>

          <section className="rounded-2xl border border-gray-200 bg-white p-5 text-xs leading-5 text-gray-500">
            <strong className="text-gray-700">Controlled-access notice:</strong> {payload.snapshot.privacy_notice} {payload.access_notice}
          </section>
        </div>
      </main>
    </div>
  );
}
