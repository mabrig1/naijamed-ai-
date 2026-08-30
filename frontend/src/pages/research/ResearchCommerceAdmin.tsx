import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { PageError, ProgressBar, Spinner, StatusBadge } from "../../components/Layout";
import { useAuth } from "../../contexts/AuthContext";

type Order = {
  id: string;
  service_name: string;
  tier_name: string;
  project_title: string;
  institution?: string;
  department?: string;
  email?: string;
  market: string;
  currency: string;
  amount_major: number;
  payment_status: string;
  status: string;
  percent_complete?: number;
  turnaround?: string;
  due_date?: string;
  notes?: string;
  dataset_link?: string;
  admin_note?: string;
  deliverables?: string[];
  receipt_number?: string;
  created_at?: string;
};

type Lead = {
  id: string;
  full_name: string;
  email: string;
  whatsapp?: string;
  service_id?: string;
  market?: string;
  message?: string;
  status?: string;
  created_at?: string;
};

const STATUSES = ["awaiting_payment", "intake", "queued", "running", "review", "delivered", "revision", "closed"];

function detail(error: unknown): string {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Request failed.";
}

function money(currency: string, amount: number) {
  return new Intl.NumberFormat(currency === "NGN" ? "en-NG" : "en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

export default function ResearchCommerceAdmin() {
  const { user } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selected, setSelected] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [edit, setEdit] = useState({ status: "intake", percent_complete: 10, due_date: "", admin_note: "", deliverables: "" });

  async function load() {
    setLoading(true);
    setError("");
    try {
      const { data } = await api.post<{ orders: Order[]; leads: Lead[] }>("/api/research-commerce", { action: "admin_orders" });
      setOrders(data.orders);
      setLeads(data.leads);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function openOrder(order: Order) {
    setSelected(order);
    setEdit({
      status: order.status,
      percent_complete: order.percent_complete ?? 0,
      due_date: order.due_date ?? "",
      admin_note: order.admin_note ?? "",
      deliverables: (order.deliverables ?? []).join("\n"),
    });
    setMessage("");
  }

  async function saveOrder() {
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      const { data } = await api.post<{ message: string }>("/api/research-commerce", {
        action: "admin_update_order",
        order_id: selected.id,
        status: edit.status,
        percent_complete: edit.percent_complete,
        due_date: edit.due_date || undefined,
        admin_note: edit.admin_note,
        deliverables: edit.deliverables.split("\n").map((row) => row.trim()).filter(Boolean),
      });
      setMessage(data.message);
      await load();
      setSelected(null);
    } catch (err: unknown) {
      setError(detail(err));
    } finally {
      setSaving(false);
    }
  }

  if (String(user?.role) !== "admin") {
    return <PageError message="Admin access is required for the research commerce fulfillment dashboard." />;
  }

  if (loading) return <div className="flex min-h-[50vh] items-center justify-center"><Spinner /></div>;

  const paidOrders = orders.filter((order) => order.payment_status === "paid");
  const revenueNgn = paidOrders.filter((order) => order.currency === "NGN").reduce((sum, order) => sum + order.amount_major, 0);
  const revenueUsd = paidOrders.filter((order) => order.currency === "USD").reduce((sum, order) => sum + order.amount_major, 0);
  const active = paidOrders.filter((order) => !["delivered", "closed"].includes(order.status)).length;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-forest-800 p-7 text-white shadow-lg">
        <div className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">Revenue operations</div>
        <h1 className="mt-2 text-3xl font-bold">Bioinformatics Commerce Admin</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-forest-100">Convert paid projects into on-time deliverables: scope intake, schedule work, publish progress, attach final files and close the order.</p>
      </section>

      {message && <div className="rounded-xl border border-forest-200 bg-forest-50 p-4 text-sm text-forest-800">✓ {message}</div>}
      {error && <PageError message={error} />}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="card"><div className="text-sm text-gray-500">Paid orders</div><div className="mt-2 text-3xl font-bold text-forest-800">{paidOrders.length}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Active projects</div><div className="mt-2 text-3xl font-bold text-forest-800">{active}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Collected NGN</div><div className="mt-2 text-2xl font-bold text-forest-800">{money("NGN", revenueNgn)}</div></div>
        <div className="card"><div className="text-sm text-gray-500">Collected USD</div><div className="mt-2 text-2xl font-bold text-forest-800">{money("USD", revenueUsd)}</div></div>
      </section>

      <section className="rounded-2xl border border-forest-100 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <div><h2 className="text-xl font-bold text-forest-800">Orders</h2><p className="mt-1 text-sm text-gray-500">Paid and pending service requests.</p></div>
          <button className="btn-secondary" onClick={load}>Refresh</button>
        </div>
        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-sm">
            <thead className="border-b border-gray-100 text-xs uppercase text-gray-400"><tr><th className="py-3 pr-3">Project</th><th className="py-3 pr-3">Client</th><th className="py-3 pr-3">Value</th><th className="py-3 pr-3">Payment</th><th className="py-3 pr-3">Status</th><th className="py-3 pr-3">Progress</th><th className="py-3">Action</th></tr></thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id} className="border-b border-gray-50 align-top">
                  <td className="py-4 pr-3"><div className="font-semibold">{order.project_title}</div><div className="mt-1 text-xs text-gray-500">{order.service_name} · {order.tier_name}</div><div className="mt-1 text-[11px] text-gray-400">{order.id}</div></td>
                  <td className="py-4 pr-3"><div>{order.email}</div><div className="text-xs text-gray-500">{order.institution || "—"} {order.department ? `· ${order.department}` : ""}</div></td>
                  <td className="py-4 pr-3 font-semibold">{money(order.currency, order.amount_major)}</td>
                  <td className="py-4 pr-3"><StatusBadge status={order.payment_status} /></td>
                  <td className="py-4 pr-3"><StatusBadge status={order.status} /></td>
                  <td className="w-44 py-4 pr-3"><ProgressBar value={order.percent_complete ?? 0} /></td>
                  <td className="py-4"><button className="btn-primary" onClick={() => openOrder(order)}>Manage</button></td>
                </tr>
              ))}
            </tbody>
          </table>
          {orders.length === 0 && <div className="py-8 text-center text-sm text-gray-500">No commerce orders yet.</div>}
        </div>
      </section>

      <section className="rounded-2xl border border-forest-100 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-bold text-forest-800">Sales leads</h2>
        <p className="mt-1 text-sm text-gray-500">Visitors who requested a custom scope before payment.</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {leads.map((lead) => (
            <article key={lead.id} className="rounded-xl border border-gray-100 p-4">
              <div className="font-semibold">{lead.full_name}</div>
              <div className="mt-1 text-sm text-forest-700">{lead.email}</div>
              {lead.whatsapp && <div className="mt-1 text-sm text-gray-600">WhatsApp: {lead.whatsapp}</div>}
              <div className="mt-2 text-xs text-gray-400">{lead.market ?? "local"} · {lead.service_id ?? "custom scope"}</div>
              {lead.message && <p className="mt-3 text-sm leading-6 text-gray-600">{lead.message}</p>}
            </article>
          ))}
          {leads.length === 0 && <div className="text-sm text-gray-500">No captured leads yet.</div>}
        </div>
      </section>

      {selected && (
        <div className="fixed inset-0 z-[100] overflow-y-auto bg-black/60 p-4" onClick={() => setSelected(null)}>
          <div className="mx-auto my-6 w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between gap-4"><div><div className="text-xs text-gray-400">{selected.id}</div><h2 className="mt-1 text-2xl font-bold">{selected.project_title}</h2><p className="mt-1 text-sm text-gray-500">{selected.service_name} · {selected.tier_name}</p></div><button className="text-2xl text-gray-400" onClick={() => setSelected(null)}>×</button></div>
            <div className="mt-5 grid gap-3 rounded-xl bg-cream p-4 text-sm sm:grid-cols-2"><div><strong>Client:</strong> {selected.email}</div><div><strong>Paid:</strong> {money(selected.currency, selected.amount_major)}</div><div><strong>Receipt:</strong> {selected.receipt_number ?? "pending"}</div><div><strong>Turnaround:</strong> {selected.turnaround ?? "scope review"}</div></div>
            {selected.notes && <div className="mt-4 rounded-xl border border-gray-100 p-4 text-sm leading-6"><strong>Client instructions</strong><p className="mt-2 whitespace-pre-wrap text-gray-600">{selected.notes}</p></div>}
            {selected.dataset_link && <a className="mt-3 block text-sm font-semibold text-forest-700 underline" href={selected.dataset_link} target="_blank" rel="noreferrer">Open client dataset link</a>}
            <div className="mt-6 space-y-4">
              <div><label className="label">Project status</label><select className="input" value={edit.status} onChange={(e) => setEdit((v) => ({ ...v, status: e.target.value }))}>{STATUSES.map((status) => <option key={status} value={status}>{status.split("_").join(" ")}</option>)}</select></div>
              <div><label className="label">Progress: {edit.percent_complete}%</label><input className="w-full" type="range" min="0" max="100" value={edit.percent_complete} onChange={(e) => setEdit((v) => ({ ...v, percent_complete: Number(e.target.value) }))} /></div>
              <div><label className="label">Target delivery date</label><input className="input" type="date" value={edit.due_date} onChange={(e) => setEdit((v) => ({ ...v, due_date: e.target.value }))} /></div>
              <div><label className="label">Client-facing progress note</label><textarea className="input min-h-24" value={edit.admin_note} onChange={(e) => setEdit((v) => ({ ...v, admin_note: e.target.value }))} placeholder="Example: Target preparation completed; docking batch is running." /></div>
              <div><label className="label">Deliverables</label><textarea className="input min-h-28" value={edit.deliverables} onChange={(e) => setEdit((v) => ({ ...v, deliverables: e.target.value }))} placeholder="One secure file URL or delivery note per line" /><p className="mt-1 text-xs text-gray-400">Use access-controlled Drive/R2/other secure links for client files.</p></div>
              <button className="btn-primary flex w-full items-center justify-center gap-2" disabled={saving} onClick={saveOrder}>{saving ? <><Spinner /> Saving…</> : "Publish project update"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
