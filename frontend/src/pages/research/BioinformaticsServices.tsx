import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useAuth } from "../../contexts/AuthContext";
import { ProgressBar, Spinner, StatusBadge } from "../../components/Layout";

type Tier = {
  id: string;
  name: string;
  local_ngn: number;
  global_usd: number;
  turnaround: string;
  scope: string;
};

type Service = {
  id: string;
  category: string;
  name: string;
  short: string;
  featured?: boolean;
  deliverables: string[];
  tiers: Tier[];
  sales_note?: string;
};

type Addon = {
  id: string;
  name: string;
  description: string;
  percent?: number;
  local_ngn?: number;
  global_usd?: number;
};

type Catalog = {
  studio: string;
  services: Service[];
  addons: Addon[];
  integrity_notice: string;
};

type Quote = {
  service_name: string;
  tier_name: string;
  currency: "NGN" | "USD";
  amount_major: number;
  turnaround: string;
  scope: string;
  addons: { id: string; name: string; amount_major: number }[];
  deliverables: string[];
};

type CommerceOrder = {
  id: string;
  service_name: string;
  tier_name: string;
  project_title: string;
  currency: string;
  amount_major: number;
  status: string;
  payment_status: string;
  percent_complete?: number;
  receipt_number?: string;
  due_date?: string;
  admin_note?: string;
  deliverables?: string[];
};

function money(currency: string, amount: number) {
  return new Intl.NumberFormat(currency === "NGN" ? "en-NG" : "en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed. Please try again.";
}

export default function BioinformaticsServices() {
  const { isAuthenticated, user } = useAuth();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [market, setMarket] = useState<"local" | "global">("local");
  const [selected, setSelected] = useState<Service | null>(null);
  const [tierId, setTierId] = useState("");
  const [addonIds, setAddonIds] = useState<string[]>([]);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [orders, setOrders] = useState<CommerceOrder[]>([]);
  const [orderForm, setOrderForm] = useState({
    project_title: "",
    institution: "",
    department: "",
    notes: "",
    dataset_link: "",
    gateway: "paystack",
  });
  const [lead, setLead] = useState({ full_name: "", email: "", whatsapp: "", message: "", website: "" });
  const [leadLoading, setLeadLoading] = useState(false);

  useEffect(() => {
    api.get<Catalog>("/api/research-commerce")
      .then(({ data }) => setCatalog(data))
      .catch((err: unknown) => setError(detail(err)));
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    api.post<{ orders: CommerceOrder[] }>("/api/research-commerce", { action: "my_orders" })
      .then(({ data }) => setOrders(data.orders))
      .catch(() => undefined);
  }, [isAuthenticated]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const reference = params.get("reference") ?? params.get("trxref") ?? params.get("tx_ref");
    const transactionId = params.get("transaction_id");
    if (!reference || !isAuthenticated) return;
    setMessage("Verifying payment…");
    api.post<{ message: string }>("/api/research-commerce", {
      action: "verify_order",
      reference,
      transaction_id: transactionId || undefined,
    })
      .then(({ data }) => {
        setMessage(data.message);
        return api.post<{ orders: CommerceOrder[] }>("/api/research-commerce", { action: "my_orders" });
      })
      .then(({ data }) => setOrders(data.orders))
      .catch((err: unknown) => setError(detail(err)))
      .finally(() => window.history.replaceState({}, "", "/bioinformatics-services"));
  }, [isAuthenticated]);

  const categories = useMemo(() => {
    const grouped = new Map<string, Service[]>();
    for (const service of catalog?.services ?? []) {
      const rows = grouped.get(service.category) ?? [];
      rows.push(service);
      grouped.set(service.category, rows);
    }
    return grouped;
  }, [catalog]);

  async function chooseService(service: Service) {
    setSelected(service);
    setTierId(service.tiers[0]?.id ?? "");
    setAddonIds([]);
    setQuote(null);
    setError("");
    setOrderForm((current) => ({ ...current, gateway: market === "global" ? "flutterwave" : "paystack" }));
    if (service.tiers[0]) await requestQuote(service.id, service.tiers[0].id, []);
  }

  async function requestQuote(serviceId: string, nextTierId: string, nextAddonIds: string[]) {
    setLoadingQuote(true);
    setError("");
    try {
      const { data } = await api.post<Quote>("/api/research-commerce", {
        action: "quote",
        service_id: serviceId,
        tier_id: nextTierId,
        market,
        addon_ids: nextAddonIds,
      });
      setQuote(data);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoadingQuote(false);
    }
  }

  async function changeTier(nextTierId: string) {
    if (!selected) return;
    setTierId(nextTierId);
    await requestQuote(selected.id, nextTierId, addonIds);
  }

  async function toggleAddon(addonId: string) {
    if (!selected) return;
    const next = addonIds.includes(addonId) ? addonIds.filter((id) => id !== addonId) : [...addonIds, addonId];
    setAddonIds(next);
    await requestQuote(selected.id, tierId, next);
  }

  async function startCheckout() {
    if (!selected || !quote || !tierId) return;
    if (!isAuthenticated) {
      setError("Create a free account or sign in before paying so your project and deliverables can be tracked securely.");
      return;
    }
    setCheckoutLoading(true);
    setError("");
    try {
      const { data } = await api.post<{ authorization_url: string }>("/api/research-commerce", {
        action: "create_order",
        service_id: selected.id,
        tier_id: tierId,
        market,
        addon_ids: addonIds,
        gateway: orderForm.gateway,
        project_title: orderForm.project_title || undefined,
        institution: orderForm.institution || undefined,
        department: orderForm.department || undefined,
        notes: orderForm.notes || undefined,
        dataset_link: orderForm.dataset_link || undefined,
        callback_url: `${window.location.origin}/bioinformatics-services`,
      });
      if (data.authorization_url) window.location.assign(data.authorization_url);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setCheckoutLoading(false);
    }
  }

  async function captureLead() {
    setLeadLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await api.post<{ message: string }>("/api/research-commerce", {
        action: "capture_lead",
        full_name: lead.full_name,
        email: lead.email,
        whatsapp: lead.whatsapp || undefined,
        message: lead.message || undefined,
        website: lead.website || undefined,
        service_id: selected?.id,
        market,
      });
      setMessage(data.message);
      setLead({ full_name: "", email: "", whatsapp: "", message: "", website: "" });
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLeadLoading(false);
    }
  }

  async function changeMarket(next: "local" | "global") {
    setMarket(next);
    setOrderForm((current) => ({ ...current, gateway: next === "global" ? "flutterwave" : "paystack" }));
    if (selected && tierId) {
      setLoadingQuote(true);
      try {
        const { data } = await api.post<Quote>("/api/research-commerce", {
          action: "quote",
          service_id: selected.id,
          tier_id: tierId,
          market: next,
          addon_ids: addonIds,
        });
        setQuote(data);
      } catch (err: unknown) {
        setError(detail(err));
      } finally {
        setLoadingQuote(false);
      }
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
              <div className="text-xs text-forest-200">Bioinformatics Consulting & Data Analysis</div>
            </div>
          </Link>
          <div className="flex items-center gap-2 text-sm">
            {isAuthenticated ? (
              <>
                <Link className="rounded-lg border border-forest-600 px-3 py-2 hover:bg-forest-800" to="/dashboard">Dashboard</Link>
                {String(user?.role) === "admin" && <Link className="rounded-lg bg-gold-400 px-3 py-2 font-semibold text-forest-900" to="/research-commerce/admin">Admin orders</Link>}
              </>
            ) : (
              <>
                <Link className="rounded-lg border border-forest-600 px-3 py-2 hover:bg-forest-800" to="/login">Sign in</Link>
                <Link className="rounded-lg bg-gold-400 px-3 py-2 font-semibold text-forest-900" to="/register">Create account</Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <section className="bg-forest-800 text-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[1.2fr_0.8fr] lg:py-16">
            <div>
              <div className="inline-flex rounded-full bg-gold-300/15 px-3 py-1 text-xs font-semibold text-gold-300">Nigeria-based · Global delivery</div>
              <h1 className="mt-4 max-w-4xl text-4xl font-bold leading-tight md:text-6xl">Bioinformatics analysis you can order, track and defend.</h1>
              <p className="mt-5 max-w-3xl text-base leading-7 text-forest-100 md:text-lg">
                Network pharmacology, ADMET screening, molecular docking, Cytoscape networks and publication-ready 3D figures for M.Sc., Ph.D., research groups and academic departments.
              </p>
              <div className="mt-7 flex flex-wrap gap-2 text-sm text-forest-100">
                {["Reproducible methods", "Defined deliverables", "Local & international checkout", "Tracked project delivery", "300-600 DPI figures"].map((item) => (
                  <span key={item} className="rounded-full border border-forest-500 px-3 py-1.5">✓ {item}</span>
                ))}
              </div>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/10 p-6 backdrop-blur-sm">
              <div className="text-sm font-semibold text-gold-300">Choose your market</div>
              <div className="mt-4 grid grid-cols-2 gap-2 rounded-xl bg-forest-900/50 p-1">
                <button className={`rounded-lg px-3 py-3 text-sm font-semibold ${market === "local" ? "bg-white text-forest-900" : "text-white"}`} onClick={() => changeMarket("local")}>🇳🇬 Nigeria · NGN</button>
                <button className={`rounded-lg px-3 py-3 text-sm font-semibold ${market === "global" ? "bg-white text-forest-900" : "text-white"}`} onClick={() => changeMarket("global")}>🌍 Global · USD</button>
              </div>
              <div className="mt-6 grid gap-3 text-sm">
                <div className="rounded-xl bg-white/10 p-4"><strong>Fastest entry offer:</strong> paid scope consultation from {market === "local" ? "₦25,000" : "$39"}.</div>
                <div className="rounded-xl bg-white/10 p-4"><strong>Core revenue offer:</strong> docking, network pharmacology and thesis computational packages.</div>
                <div className="rounded-xl bg-white/10 p-4"><strong>Institutional offer:</strong> 30-day department analysis bundle for multiple projects.</div>
              </div>
            </div>
          </div>
        </section>

        <div className="mx-auto max-w-7xl space-y-12 px-4 py-10 sm:px-6">
          {message && <div className="rounded-2xl border border-forest-200 bg-forest-50 p-4 text-sm font-medium text-forest-800">✓ {message}</div>}
          {error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">⚠️ {error}</div>}

          {[...categories.entries()].map(([category, services]) => (
            <section key={category}>
              <div className="mb-5">
                <h2 className="text-2xl font-bold text-forest-800">{category}</h2>
                <p className="mt-1 text-sm text-gray-500">Defined scope, visible starting price and traceable outputs.</p>
              </div>
              <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {services.map((service) => {
                  const first = service.tiers[0];
                  return (
                    <article key={service.id} className={`card flex h-full flex-col border ${service.featured ? "border-gold-300 shadow-md" : "border-forest-100"}`}>
                      {service.featured && <div className="mb-2 text-xs font-bold uppercase tracking-wide text-gold-600">High-demand offer</div>}
                      <h3 className="text-xl font-bold text-gray-900">{service.name}</h3>
                      <p className="mt-3 flex-1 text-sm leading-6 text-gray-600">{service.short}</p>
                      <ul className="mt-4 space-y-1.5 text-sm text-gray-600">
                        {service.deliverables.slice(0, 5).map((item) => <li key={item}>✓ {item}</li>)}
                      </ul>
                      <div className="mt-5 rounded-xl bg-cream p-3 text-sm">
                        <div className="font-semibold text-forest-800">{first.name}</div>
                        <div className="mt-1 text-xs text-gray-500">{first.scope}</div>
                        <div className="mt-2 text-lg font-bold text-forest-700">From {market === "local" ? money("NGN", first.local_ngn) : money("USD", first.global_usd)}</div>
                        <div className="text-xs text-gray-500">{first.turnaround}</div>
                      </div>
                      <button className="btn-primary mt-5" onClick={() => chooseService(service)}>Get instant quote / order</button>
                    </article>
                  );
                })}
              </div>
            </section>
          ))}

          {isAuthenticated && orders.length > 0 && (
            <section className="rounded-3xl border border-forest-100 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-end justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-bold text-forest-800">Your paid research projects</h2>
                  <p className="mt-1 text-sm text-gray-500">Track progress, receipt numbers and final deliverables.</p>
                </div>
              </div>
              <div className="mt-6 grid gap-4 lg:grid-cols-2">
                {orders.map((order) => (
                  <article key={order.id} className="rounded-2xl border border-gray-100 p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-xs text-gray-400">{order.id}</div>
                        <h3 className="mt-1 font-bold text-gray-900">{order.project_title}</h3>
                        <p className="mt-1 text-sm text-gray-500">{order.service_name} · {order.tier_name}</p>
                      </div>
                      <StatusBadge status={order.status} />
                    </div>
                    <div className="mt-4"><ProgressBar value={order.percent_complete ?? 0} label="Project progress" /></div>
                    <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                      <div className="rounded-lg bg-cream p-3"><div className="text-xs text-gray-400">Paid / quoted</div><div className="font-semibold">{money(order.currency, order.amount_major)}</div></div>
                      <div className="rounded-lg bg-cream p-3"><div className="text-xs text-gray-400">Receipt</div><div className="font-semibold">{order.receipt_number ?? "Pending payment"}</div></div>
                    </div>
                    {order.due_date && <p className="mt-3 text-sm text-gray-600"><strong>Target delivery:</strong> {order.due_date}</p>}
                    {order.admin_note && <div className="mt-3 rounded-lg bg-forest-50 p-3 text-sm text-forest-800">{order.admin_note}</div>}
                    {(order.deliverables?.length ?? 0) > 0 && (
                      <div className="mt-4">
                        <div className="text-sm font-semibold text-gray-800">Deliverables</div>
                        <div className="mt-2 space-y-2 text-sm">
                          {order.deliverables?.map((item) => item.startsWith("http") ? <a key={item} className="block text-forest-700 underline" href={item} target="_blank" rel="noreferrer">Open deliverable</a> : <div key={item}>{item}</div>)}
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            </section>
          )}

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-3xl bg-forest-900 p-7 text-white">
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">Not sure what to order?</div>
              <h2 className="mt-3 text-3xl font-bold">Send your project brief for a custom scope.</h2>
              <p className="mt-4 text-sm leading-7 text-forest-100">Useful for unusual datasets, multi-target docking, departmental projects, grant-linked computational work or projects that exceed the published package limits.</p>
              <div className="mt-6 grid gap-3 text-sm text-forest-100 sm:grid-cols-2">
                <div className="rounded-xl bg-white/10 p-4">M.Sc. / Ph.D. projects</div>
                <div className="rounded-xl bg-white/10 p-4">University departments</div>
                <div className="rounded-xl bg-white/10 p-4">Research groups & NGOs</div>
                <div className="rounded-xl bg-white/10 p-4">Herbal/drug discovery teams</div>
              </div>
            </div>
            <div className="card border border-forest-100">
              <div className="space-y-4">
                <div><label className="label">Name</label><input className="input" value={lead.full_name} onChange={(e) => setLead((v) => ({ ...v, full_name: e.target.value }))} /></div>
                <div><label className="label">Email</label><input className="input" type="email" value={lead.email} onChange={(e) => setLead((v) => ({ ...v, email: e.target.value }))} /></div>
                <div><label className="label">WhatsApp, optional</label><input className="input" value={lead.whatsapp} onChange={(e) => setLead((v) => ({ ...v, whatsapp: e.target.value }))} placeholder="Include country code for international numbers" /></div>
                <div><label className="label">Project brief</label><textarea className="input min-h-28" value={lead.message} onChange={(e) => setLead((v) => ({ ...v, message: e.target.value }))} placeholder="Research question, compounds/plants, targets, dataset size, deadline and required outputs" /></div>
                <input className="hidden" tabIndex={-1} autoComplete="off" value={lead.website} onChange={(e) => setLead((v) => ({ ...v, website: e.target.value }))} />
                <button className="btn-primary flex w-full items-center justify-center gap-2" disabled={leadLoading} onClick={captureLead}>{leadLoading ? <><Spinner /> Sending…</> : "Request custom scope"}</button>
              </div>
            </div>
          </section>

          <section className="rounded-2xl border border-gold-200 bg-gold-50 p-5 text-sm leading-6 text-gray-700">
            <strong>Research integrity:</strong> {catalog.integrity_notice}
          </section>
        </div>
      </main>

      <footer className="bg-forest-950 bg-forest-900 px-4 py-8 text-center text-sm text-forest-300">
        NigerFlora BioSciences · Bioinformatics Consulting & Data Analysis · Powered by MABRIG Technologies
      </footer>

      {selected && (
        <div className="fixed inset-0 z-[100] overflow-y-auto bg-black/60 p-4" onClick={() => setSelected(null)}>
          <div className="mx-auto my-6 w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-xs font-bold uppercase tracking-wide text-forest-500">Instant quote</div>
                <h2 className="mt-1 text-2xl font-bold">{selected.name}</h2>
              </div>
              <button className="text-2xl text-gray-400" onClick={() => setSelected(null)}>×</button>
            </div>

            <div className="mt-5 space-y-5">
              <div>
                <label className="label">Package tier</label>
                <select className="input" value={tierId} onChange={(e) => changeTier(e.target.value)}>
                  {selected.tiers.map((tier) => <option key={tier.id} value={tier.id}>{tier.name} — {tier.scope}</option>)}
                </select>
              </div>

              <div>
                <div className="label">Optional add-ons</div>
                <div className="space-y-2">
                  {catalog.addons.map((addon) => (
                    <label key={addon.id} className="flex cursor-pointer gap-3 rounded-xl border border-gray-200 p-3">
                      <input type="checkbox" checked={addonIds.includes(addon.id)} onChange={() => toggleAddon(addon.id)} />
                      <span><span className="font-semibold">{addon.name}</span><span className="block text-xs text-gray-500">{addon.description}</span></span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl bg-forest-50 p-5">
                {loadingQuote ? <Spinner /> : quote && (
                  <>
                    <div className="flex items-end justify-between gap-4"><div><div className="text-sm text-gray-500">Quoted total</div><div className="text-3xl font-bold text-forest-800">{money(quote.currency, quote.amount_major)}</div></div><div className="text-right text-sm"><div className="font-semibold">{quote.turnaround}</div><div className="text-gray-500">{quote.scope}</div></div></div>
                    {quote.addons.length > 0 && <div className="mt-3 text-xs text-gray-500">Includes: {quote.addons.map((row) => row.name).join(", ")}</div>}
                  </>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div><label className="label">Project title</label><input className="input" value={orderForm.project_title} onChange={(e) => setOrderForm((v) => ({ ...v, project_title: e.target.value }))} /></div>
                <div><label className="label">Institution</label><input className="input" value={orderForm.institution} onChange={(e) => setOrderForm((v) => ({ ...v, institution: e.target.value }))} /></div>
              </div>
              <div><label className="label">Department / Lab</label><input className="input" value={orderForm.department} onChange={(e) => setOrderForm((v) => ({ ...v, department: e.target.value }))} /></div>
              <div><label className="label">Project instructions</label><textarea className="input min-h-28" value={orderForm.notes} onChange={(e) => setOrderForm((v) => ({ ...v, notes: e.target.value }))} placeholder="Compounds/plants, targets, dataset size, deadline, journal/thesis needs and expected outputs" /></div>
              <div><label className="label">Dataset / files link, optional</label><input className="input" type="url" value={orderForm.dataset_link} onChange={(e) => setOrderForm((v) => ({ ...v, dataset_link: e.target.value }))} placeholder="https://drive.google.com/... or another access-controlled link" /></div>
              <div>
                <label className="label">Payment gateway</label>
                <select className="input" value={orderForm.gateway} onChange={(e) => setOrderForm((v) => ({ ...v, gateway: e.target.value }))}>
                  <option value="paystack">Paystack {market === "local" ? "— recommended for Nigeria" : "— international/foreign card if enabled"}</option>
                  <option value="flutterwave">Flutterwave {market === "global" ? "— recommended for international checkout" : "— alternative"}</option>
                </select>
              </div>

              {!isAuthenticated && (
                <div className="rounded-xl border border-gold-200 bg-gold-50 p-4 text-sm">
                  To pay and track delivery, <Link className="font-semibold text-forest-700 underline" to="/register">create a free account</Link> or <Link className="font-semibold text-forest-700 underline" to="/login">sign in</Link>.
                </div>
              )}

              <button className="btn-primary flex w-full items-center justify-center gap-2" disabled={checkoutLoading || !quote} onClick={startCheckout}>
                {checkoutLoading ? <><Spinner /> Opening secure checkout…</> : isAuthenticated ? "Pay & start project" : "Create account before payment"}
              </button>
              {selected.sales_note && <p className="text-xs text-gray-500">{selected.sales_note}</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
