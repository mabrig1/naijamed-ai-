import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { PageError, Spinner } from "../../components/Layout";
import { useAuth } from "../../contexts/AuthContext";

type Summary = {
  period: string;
  subscriptions: {
    active_total: number;
    family_pass_active: number;
    doctor_workspace_active: number;
    mrr_ngn_kobo: number;
  };
  consultations: {
    paid_this_month: number;
    gmv_ngn_kobo: number;
    platform_fees_ngn_kobo: number;
    commission_percent: number;
  };
  research_services: {
    paid_orders_this_month: number;
    revenue_by_currency: Record<string, number>;
    new_leads: number;
  };
};

function naira(kobo: number) {
  return new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 }).format(kobo / 100);
}

function majorMoney(currency: string, amount: number) {
  return new Intl.NumberFormat(currency === "NGN" ? "en-NG" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function MonetizationAdmin() {
  const { user } = useAuth();
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (String(user?.role) !== "admin") return;
    api.get<Summary>("/api/admin/monetization/summary")
      .then(({ data }) => setSummary(data))
      .catch((err: unknown) => setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Could not load revenue metrics."));
  }, [user]);

  if (String(user?.role) !== "admin") {
    return <PageError message="Administrator access is required for monetization metrics." />;
  }
  if (error) return <PageError message={error} />;
  if (!summary) return <div className="flex h-64 items-center justify-center"><Spinner /></div>;

  const researchRows = Object.entries(summary.research_services.revenue_by_currency);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-forest-600">Commercial control room</div>
          <h1 className="mt-2 text-3xl font-bold text-forest-900">Monetization Dashboard</h1>
          <p className="mt-2 text-sm text-gray-500">Revenue and conversion signals for {summary.period}.</p>
        </div>
        <div className="flex gap-2">
          <Link className="btn-outline" to="/pricing">Public pricing</Link>
          <Link className="btn-primary" to="/research-commerce/admin">Research orders</Link>
        </div>
      </div>

      <section>
        <h2 className="mb-4 text-xl font-bold text-forest-800">Recurring revenue</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="card"><div className="text-sm text-gray-500">Monthly recurring revenue</div><div className="mt-2 text-3xl font-bold text-forest-800">{naira(summary.subscriptions.mrr_ngn_kobo)}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Active subscriptions</div><div className="mt-2 text-3xl font-bold">{summary.subscriptions.active_total}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Family Health Pass</div><div className="mt-2 text-3xl font-bold">{summary.subscriptions.family_pass_active}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Doctor Workspace</div><div className="mt-2 text-3xl font-bold">{summary.subscriptions.doctor_workspace_active}</div></div>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold text-forest-800">Consultation marketplace</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="card"><div className="text-sm text-gray-500">Paid consultations this month</div><div className="mt-2 text-3xl font-bold">{summary.consultations.paid_this_month}</div></div>
          <div className="card"><div className="text-sm text-gray-500">Consultation GMV</div><div className="mt-2 text-3xl font-bold">{naira(summary.consultations.gmv_ngn_kobo)}</div></div>
          <div className="card border border-gold-300"><div className="text-sm text-gray-500">Platform commission earned</div><div className="mt-2 text-3xl font-bold text-forest-800">{naira(summary.consultations.platform_fees_ngn_kobo)}</div><div className="mt-1 text-xs text-gray-400">{summary.consultations.commission_percent}% configured commission</div></div>
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-bold text-forest-800">Research services</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="card"><div className="text-sm text-gray-500">Paid orders this month</div><div className="mt-2 text-3xl font-bold">{summary.research_services.paid_orders_this_month}</div></div>
          <div className="card">
            <div className="text-sm text-gray-500">Revenue this month</div>
            <div className="mt-2 space-y-1">
              {researchRows.length ? researchRows.map(([currency, amount]) => <div key={currency} className="text-2xl font-bold text-forest-800">{majorMoney(currency, amount)}</div>) : <div className="text-2xl font-bold text-gray-400">No paid orders yet</div>}
            </div>
          </div>
          <div className="card"><div className="text-sm text-gray-500">New research leads</div><div className="mt-2 text-3xl font-bold">{summary.research_services.new_leads}</div></div>
        </div>
      </section>

      <section className="rounded-2xl border border-forest-100 bg-white p-6 text-sm leading-6 text-gray-600">
        <strong className="text-forest-800">Revenue discipline:</strong> watch MRR, consultation commission, research-service revenue, checkout conversion and churn separately. They have different margins and should not be blended into one vanity metric.
      </section>
    </div>
  );
}
