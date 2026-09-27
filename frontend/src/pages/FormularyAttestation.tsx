import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { PageError, Spinner } from "../components/Layout";

type RequestData = {
  status: string;
  expires_at?: string | null;
  researcher_name: string;
  item: {
    title?: string | null;
    category?: string | null;
    description?: string | null;
    occurred_on?: string | null;
    outcome?: string | null;
  };
  intended_verifier_name?: string | null;
  message?: string | null;
  identity_notice: string;
};

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Attestation request unavailable.";
}

export default function FormularyAttestation() {
  const { token = "" } = useParams();
  const [data, setData] = useState<RequestData | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    verifier_name: "",
    verifier_email: "",
    verifier_title: "",
    organization: "",
    comment: "",
    attest: true,
  });

  useEffect(() => {
    api.get<RequestData>(`/api/formulary/attest/${encodeURIComponent(token)}`)
      .then(({ data: payload }) => {
        setData(payload);
        setForm((current) => ({ ...current, verifier_name: payload.intended_verifier_name || "" }));
      })
      .catch((err: unknown) => setError(detail(err)));
  }, [token]);

  async function submit(attest: boolean) {
    setSubmitting(true);
    setError("");
    try {
      const { data: result } = await api.post<{ status: string; message: string }>(`/api/formulary/attest/${encodeURIComponent(token)}`, { ...form, attest });
      setMessage(result.message);
      setData((current) => current ? { ...current, status: result.status } : current);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !data) return <div className="min-h-screen bg-cream p-6"><div className="mx-auto max-w-3xl"><PageError message={error} /></div></div>;
  if (!data) return <div className="flex min-h-screen items-center justify-center bg-cream"><Spinner /></div>;

  return (
    <div className="min-h-screen bg-cream px-5 py-10">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="rounded-3xl bg-forest-900 p-7 text-white">
          <div className="text-xs font-bold uppercase tracking-[0.22em] text-gold-300">Formulary Attestation</div>
          <h1 className="mt-3 text-3xl font-bold">Review a portfolio record for {data.researcher_name}</h1>
          <p className="mt-3 text-sm leading-6 text-forest-100">{data.identity_notice}</p>
        </header>

        <section className="card">
          <div className="text-xs font-semibold uppercase text-forest-500">{data.item.category} · {data.item.occurred_on}</div>
          <h2 className="mt-2 text-2xl font-bold text-gray-900">{data.item.title}</h2>
          {data.item.description && <p className="mt-3 text-sm leading-6 text-gray-600">{data.item.description}</p>}
          {data.item.outcome && <div className="mt-4 rounded-xl bg-cream p-4 text-sm text-gray-700"><strong>Reported outcome:</strong> {data.item.outcome}</div>}
          {data.message && <div className="mt-4 rounded-xl border border-gold-200 bg-gold-50 p-4 text-sm text-gray-700"><strong>Researcher note:</strong> {data.message}</div>}
          <div className="mt-4 text-xs text-gray-400">Request status: {data.status}{data.expires_at ? ` · Expires ${new Date(data.expires_at).toLocaleString()}` : ""}</div>
        </section>

        {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
        {error && <PageError message={error} />}

        {data.status === "pending" ? (
          <section className="card">
            <h2 className="text-xl font-bold text-forest-800">Your response</h2>
            <div className="mt-4 space-y-3">
              <input className="input" value={form.verifier_name} onChange={(e) => setForm((v) => ({ ...v, verifier_name: e.target.value }))} placeholder="Your full name" />
              <input className="input" type="email" value={form.verifier_email} onChange={(e) => setForm((v) => ({ ...v, verifier_email: e.target.value }))} placeholder="Email the request was intended for" />
              <div className="grid gap-3 sm:grid-cols-2">
                <input className="input" value={form.verifier_title} onChange={(e) => setForm((v) => ({ ...v, verifier_title: e.target.value }))} placeholder="Title / role" />
                <input className="input" value={form.organization} onChange={(e) => setForm((v) => ({ ...v, organization: e.target.value }))} placeholder="Organization / institution" />
              </div>
              <textarea className="input min-h-24" value={form.comment} onChange={(e) => setForm((v) => ({ ...v, comment: e.target.value }))} placeholder="Optional comment" />
              <div className="grid gap-3 sm:grid-cols-2">
                <button className="btn-primary" disabled={submitting || !form.verifier_name || !form.verifier_email} onClick={() => submit(true)}>Attest record</button>
                <button className="btn-outline" disabled={submitting || !form.verifier_name || !form.verifier_email} onClick={() => submit(false)}>Decline</button>
              </div>
            </div>
          </section>
        ) : (
          <section className="card text-center">
            <div className="text-lg font-bold text-forest-800">This request is {data.status}.</div>
          </section>
        )}
      </div>
    </div>
  );
}
