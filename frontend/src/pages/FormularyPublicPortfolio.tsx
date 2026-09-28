import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner, StatusBadge } from "../components/Layout";

type PublicPayload = {
  researcher: {
    name: string;
    track?: string | null;
    program_name?: string | null;
    institution?: string | null;
    specialty?: string | null;
    summary?: string | null;
    start_date?: string | null;
    target_end_date?: string | null;
  };
  items: Array<{
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
    attestation_status: string;
    attested_by?: { name?: string; title?: string; organization?: string } | null;
  }>;
  summary: {
    total_items: number;
    completed_items: number;
    attested_items: number;
    total_hours: number;
  };
  verification_notice: string;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Public portfolio unavailable.";
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (match) => match.toUpperCase());
}

export default function FormularyPublicPortfolio() {
  const { slug = "" } = useParams();
  const [data, setData] = useState<PublicPayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<PublicPayload>(`/api/formulary/portfolio/public/${encodeURIComponent(slug)}`)
      .then(({ data: payload }) => setData(payload))
      .catch((err: unknown) => setError(detail(err)));
  }, [slug]);

  if (error) return <div className="min-h-screen bg-cream p-6"><div className="mx-auto max-w-4xl"><PageError message={error} /></div></div>;
  if (!data) return <div className="flex min-h-screen items-center justify-center bg-cream"><Spinner /></div>;

  return (
    <div className="min-h-screen bg-cream text-gray-900">
      <header className="bg-forest-900 text-white">
        <div className="mx-auto max-w-6xl px-5 py-12">
          <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary Public Portfolio</div>
          <h1 className="mt-3 text-4xl font-bold">{data.researcher.name}</h1>
          <p className="mt-2 text-forest-100">{data.researcher.program_name} · {data.researcher.institution}</p>
          {data.researcher.specialty && <p className="mt-1 text-sm text-forest-200">{data.researcher.specialty}</p>}
          {data.researcher.summary && <p className="mt-5 max-w-3xl text-sm leading-7 text-forest-100">{data.researcher.summary}</p>}
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-5 py-8">
        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="card"><div className="text-sm text-gray-500">Public records</div><div className="mt-2 text-3xl font-bold">{data.summary.total_items}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Completed</div><div className="mt-2 text-3xl font-bold">{data.summary.completed_items}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Attested</div><div className="mt-2 text-3xl font-bold">{data.summary.attested_items}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Logged hours</div><div className="mt-2 text-3xl font-bold">{data.summary.total_hours}</div></div>
        </section>

        <section className="space-y-4">
          {data.items.map((item) => (
            <article key={item.id} className="card">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wide text-forest-500">{titleCase(item.category)} · {item.occurred_on}</div>
                  <h2 className="mt-1 text-xl font-bold text-gray-900">{item.title}</h2>
                </div>
                <StatusBadge status={item.status === "completed" ? "active" : item.status === "in_progress" ? "pending" : "draft"} />
              </div>
              {item.description && <p className="mt-3 text-sm leading-6 text-gray-600">{item.description}</p>}
              {item.outcome && <div className="mt-4 rounded-xl bg-cream p-4 text-sm text-gray-700"><strong>Outcome / reflection:</strong> {item.outcome}</div>}
              {!!item.competencies.length && <div className="mt-4 flex flex-wrap gap-2">{item.competencies.map((name) => <span key={name} className="rounded-full bg-forest-50 px-3 py-1 text-xs text-forest-700">{name}</span>)}</div>}
              <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-500">
                {item.hours != null && <span>{item.hours} hours</span>}
                <span>Attestation: {item.attestation_status}</span>
                {item.evidence_url && <a href={item.evidence_url} target="_blank" rel="noreferrer" className="text-forest-700 underline">Evidence</a>}
              </div>
              {item.attested_by && (
                <div className="mt-4 rounded-xl border border-forest-100 bg-forest-50 p-4 text-sm text-forest-800">
                  Attested by <strong>{item.attested_by.name}</strong>{item.attested_by.title ? `, ${item.attested_by.title}` : ""}{item.attested_by.organization ? ` · ${item.attested_by.organization}` : ""}
                </div>
              )}
            </article>
          ))}
          {!data.items.length && <div className="card py-12 text-center text-gray-400">No public portfolio records yet.</div>}
        </section>

        <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
          <strong>Verification notice:</strong> {data.verification_notice}
        </section>
      </main>
    </div>
  );
}
