import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { Spinner, StatusBadge } from "../components/Layout";

type SubscriptionPlan = {
  id: "family_pass" | "doctor_workspace";
  label: string;
  audience: string;
  price_kobo: number;
  billing: string;
  paystack_plan_code?: string | null;
  allowed_roles: string[];
  features: string[];
};

type PlanCatalog = {
  currency: string;
  free: {
    id: string;
    label: string;
    price_kobo: number;
    billing: string;
    features: string[];
  };
  subscriptions: SubscriptionPlan[];
  consultations: {
    label: string;
    pricing: string;
    platform_commission_percent: number;
  };
  research_services_url: string;
  enterprise: { id: string; label: string; pricing: string }[];
};

type SubscriptionState = {
  active_plan_ids: string[];
  entitlements: string[];
  subscriptions: {
    id: string;
    plan_id: string;
    status: string;
    payment_reference?: string;
    subscription_code?: string;
    next_payment_date?: string;
  }[];
};

function naira(kobo: number) {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0,
  }).format(kobo / 100);
}

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

export default function Pricing() {
  const { isAuthenticated, user } = useAuth();
  const [catalog, setCatalog] = useState<PlanCatalog | null>(null);
  const [subscriptionState, setSubscriptionState] = useState<SubscriptionState | null>(null);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function refreshSubscriptions() {
    if (!isAuthenticated) return;
    try {
      const { data } = await api.get<SubscriptionState>("/api/clinical/subscriptions/me");
      setSubscriptionState(data);
    } catch {
      // Keep public pricing usable even if the account-status request fails.
    }
  }

  useEffect(() => {
    api.get<PlanCatalog>("/api/clinical/plans")
      .then(({ data }) => setCatalog(data))
      .catch((err: unknown) => setError(detail(err)));
  }, []);

  useEffect(() => {
    refreshSubscriptions();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reference = params.get("reference") ?? params.get("trxref");
    if (!reference || !isAuthenticated) return;

    setMessage("Confirming your subscription payment…");
    api.get<{ plan_id: string; status: string }>(`/api/clinical/subscriptions/verify/${encodeURIComponent(reference)}`)
      .then(({ data }) => {
        setMessage(`${data.plan_id === "family_pass" ? "Family Health Pass" : "Doctor Workspace"} is active.`);
        return refreshSubscriptions();
      })
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => window.history.replaceState({}, "", "/pricing"));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  async function checkout(plan: SubscriptionPlan) {
    if (!isAuthenticated) return;
    setLoadingPlan(plan.id);
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<{ authorization_url: string }>("/api/clinical/subscriptions/checkout", {
        plan_id: plan.id,
        callback_url: `${window.location.origin}/pricing`,
      });
      window.location.assign(data.authorization_url);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoadingPlan(null);
    }
  }

  if (!catalog) {
    return <div className="flex min-h-screen items-center justify-center bg-cream"><Spinner /></div>;
  }

  return (
    <div className="min-h-screen bg-cream text-gray-900">
      <header className="border-b border-forest-800 bg-forest-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <Link to="/" className="flex items-center gap-3">
            <span className="text-2xl">🌿</span>
            <div>
              <div className="font-bold text-gold-300">NigerFlora BioSciences</div>
              <div className="text-xs text-forest-200">Care plans & professional tools</div>
            </div>
          </Link>
          <div className="flex items-center gap-2 text-sm">
            <Link className="rounded-lg border border-forest-600 px-3 py-2 hover:bg-forest-800" to="/bioinformatics-services">Research services</Link>
            {isAuthenticated ? (
              <Link className="rounded-lg bg-gold-400 px-3 py-2 font-semibold text-forest-900" to="/dashboard">Dashboard</Link>
            ) : (
              <Link className="rounded-lg bg-gold-400 px-3 py-2 font-semibold text-forest-900" to="/register">Create account</Link>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="bg-forest-800 text-white">
          <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:py-20">
            <div className="max-w-4xl">
              <div className="inline-flex rounded-full bg-gold-300/15 px-3 py-1 text-xs font-semibold text-gold-300">Transparent NGN pricing · Secure Paystack checkout</div>
              <h1 className="mt-4 text-4xl font-bold leading-tight md:text-6xl">Free essential care. Paid convenience, continuity and professional workflows.</h1>
              <p className="mt-5 max-w-3xl text-base leading-7 text-forest-100 md:text-lg">
                Keep red-flag triage accessible, then monetize the higher-value layers: family continuity, doctor productivity, verified consultations and research services.
              </p>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-7xl space-y-10 px-4 py-10 sm:px-6">
          {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm font-medium text-forest-800">✓ {message}</div>}
          {error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">⚠️ {error}</div>}

          <section className="grid gap-5 lg:grid-cols-3">
            <article className="card border border-forest-100">
              <div className="text-xs font-bold uppercase tracking-wide text-forest-600">Free forever</div>
              <h2 className="mt-2 text-2xl font-bold">{catalog.free.label}</h2>
              <div className="mt-4 text-4xl font-bold text-forest-800">₦0</div>
              <p className="mt-1 text-sm text-gray-500">No subscription required</p>
              <ul className="mt-6 space-y-3 text-sm text-gray-600">
                {catalog.free.features.map((feature) => <li key={feature}>✓ {feature}</li>)}
              </ul>
              <Link to={isAuthenticated ? "/dashboard" : "/register"} className="btn-outline mt-7 block text-center">
                {isAuthenticated ? "Open dashboard" : "Create free account"}
              </Link>
            </article>

            {catalog.subscriptions.map((plan) => {
              const active = subscriptionState?.active_plan_ids.includes(plan.id) ?? false;
              const roleAllowed = !user || plan.allowed_roles.includes(String(user.role));
              return (
                <article key={plan.id} className="card border border-gold-300 shadow-md">
                  <div className="text-xs font-bold uppercase tracking-wide text-gold-600">{plan.audience}</div>
                  <h2 className="mt-2 text-2xl font-bold">{plan.label}</h2>
                  <div className="mt-4 flex items-end gap-2">
                    <span className="text-4xl font-bold text-forest-800">{naira(plan.price_kobo)}</span>
                    <span className="pb-1 text-sm text-gray-500">/ month</span>
                  </div>
                  <ul className="mt-6 space-y-3 text-sm text-gray-600">
                    {plan.features.map((feature) => <li key={feature}>✓ {feature}</li>)}
                  </ul>
                  {active ? (
                    <div className="mt-7 flex items-center justify-between rounded-xl bg-forest-50 p-3 text-sm">
                      <span className="font-semibold text-forest-800">Current plan</span>
                      <StatusBadge status="active" />
                    </div>
                  ) : !isAuthenticated ? (
                    <Link to="/register" className="btn-primary mt-7 block text-center">Create account to subscribe</Link>
                  ) : roleAllowed ? (
                    <button className="btn-primary mt-7 w-full" disabled={loadingPlan === plan.id || !plan.paystack_plan_code} onClick={() => checkout(plan)}>
                      {loadingPlan === plan.id ? "Opening secure checkout…" : plan.paystack_plan_code ? `Start ${plan.label}` : "Plan setup pending"}
                    </button>
                  ) : (
                    <div className="mt-7 rounded-xl bg-gray-100 p-3 text-sm text-gray-600">
                      This plan is designed for a different account type.
                    </div>
                  )}
                  {!plan.paystack_plan_code && <p className="mt-2 text-xs text-amber-700">Admin must add the Paystack plan code before live sales begin.</p>}
                </article>
              );
            })}
          </section>

          <section className="grid gap-5 lg:grid-cols-2">
            <article className="rounded-3xl bg-forest-900 p-7 text-white">
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">Marketplace revenue</div>
              <h2 className="mt-3 text-3xl font-bold">Paid doctor consultations</h2>
              <p className="mt-4 text-sm leading-7 text-forest-100">
                Verified providers set their consultation fees. NigerFlora records the checkout, assigns the case after verified payment and retains a {catalog.consultations.platform_commission_percent}% platform commission.
              </p>
              <Link to={isAuthenticated ? "/dashboard" : "/register"} className="mt-6 inline-block rounded-xl bg-gold-400 px-5 py-3 text-sm font-bold text-forest-900">
                {isAuthenticated ? "Open care dashboard" : "Join NigerFlora"}
              </Link>
            </article>

            <article className="rounded-3xl border border-forest-100 bg-white p-7 shadow-sm">
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-forest-600">High-ticket revenue</div>
              <h2 className="mt-3 text-3xl font-bold text-forest-900">Bioinformatics & research services</h2>
              <p className="mt-4 text-sm leading-7 text-gray-600">
                Keep subscriptions as recurring revenue while research consulting drives larger one-off transactions through ADMET, network pharmacology, docking and postgraduate computational packages.
              </p>
              <Link to={catalog.research_services_url} className="btn-primary mt-6 inline-block">View services & prices →</Link>
            </article>
          </section>

          <section className="rounded-3xl border border-forest-100 bg-white p-7">
            <h2 className="text-2xl font-bold text-forest-900">Institutional revenue</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
              Clinics, HMOs, campuses and employers can move to contract pricing once usage and support requirements are known. Keep these deals quote-based rather than forcing them into a consumer subscription.
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {catalog.enterprise.map((item) => (
                <div key={item.id} className="rounded-xl bg-cream p-4">
                  <div className="font-semibold text-forest-800">{item.label}</div>
                  <div className="mt-1 text-sm text-gray-500">{item.pricing}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
            <strong>Clinical boundary:</strong> subscriptions buy workflow, continuity and access features. They do not guarantee a diagnosis, treatment result, emergency response time or clinician availability. Emergency red flags should continue to route users to appropriate urgent care.
          </section>
        </div>
      </main>
    </div>
  );
}
