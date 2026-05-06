import { useState } from "react";
import {
  useMyEscrowTransactions,
  useReleaseEscrow,
  useRaiseDispute,
  useDisputes,
  useResolveDispute,
} from "../../hooks/useEscrow";
import type { EscrowTransaction, EscrowStatus, DisputeListItem } from "../../hooks/useEscrow";
import { useAuth } from "../../hooks/useAuth";
import { Spinner, Empty, PageError } from "../../components/Layout";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<EscrowStatus, { label: string; color: string; icon: string }> = {
  held:                 { label: "Funds Held",          color: "bg-blue-100 text-blue-700",      icon: "🔒" },
  delivery_confirmed:   { label: "Delivery Confirmed",  color: "bg-amber-100 text-amber-700",    icon: "📦" },
  released:             { label: "Released",            color: "bg-forest-100 text-forest-700",  icon: "✅" },
  disputed:             { label: "In Dispute",          color: "bg-red-100 text-red-700",        icon: "⚖️" },
  refunded:             { label: "Refunded",            color: "bg-purple-100 text-purple-700",  icon: "↩️" },
  auto_released:        { label: "Auto-Released",       color: "bg-gray-100 text-gray-600",      icon: "🕒" },
};

function StatusBadge({ status }: { status: EscrowStatus }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: "bg-gray-100 text-gray-600", icon: "❓" };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ── Release modal ─────────────────────────────────────────────────────────────

function ReleaseModal({
  escrow,
  onClose,
}: {
  escrow: EscrowTransaction;
  onClose: () => void;
}) {
  const [note, setNote] = useState("");
  const releaseMut = useReleaseEscrow();

  async function handleRelease() {
    await releaseMut.mutateAsync({
      order_id: escrow.order_id,
      confirmation_note: note || undefined,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="bg-forest-600 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-white font-bold">✅ Confirm Delivery & Release Funds</h3>
            <p className="text-forest-200 text-xs mt-0.5">Order #{escrow.order_id}</p>
          </div>
          <button onClick={onClose} className="text-forest-200 hover:text-white text-xl">✕</button>
        </div>

        {releaseMut.isSuccess ? (
          <div className="p-6 text-center space-y-4">
            <div className="text-5xl">✅</div>
            <h4 className="font-bold text-forest-700 text-lg">Funds Released!</h4>
            <p className="text-gray-500 text-sm">Payment of ${escrow.amount_usd} has been released to the seller.</p>
            <p className="text-xs text-amber-600">⏳ 48-hour dispute window is now open.</p>
            <button onClick={onClose} className="btn-primary w-full">Close</button>
          </div>
        ) : (
          <div className="p-6 space-y-4">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm">
              <p className="font-semibold text-amber-800 mb-1">⚠️ This action is irreversible</p>
              <p className="text-amber-700">
                By confirming delivery, you authorise the release of{" "}
                <strong>${escrow.amount_usd}</strong> to the seller.
                A 48-hour dispute window opens after release.
              </p>
            </div>
            <div>
              <label className="label">Confirmation note (optional)</label>
              <textarea className="input min-h-20 resize-none text-sm"
                placeholder="e.g. Herbs received in good condition, quality as described..."
                value={note}
                onChange={(e) => setNote(e.target.value)} />
            </div>
            {releaseMut.isError && (
              <p className="text-red-600 text-sm">⚠️ Release failed. Please try again.</p>
            )}
            <div className="flex gap-3">
              <button onClick={handleRelease} className="btn-primary flex-1"
                disabled={releaseMut.isPending}>
                {releaseMut.isPending ? <Spinner /> : "✅ Confirm & Release"}
              </button>
              <button onClick={onClose} className="btn-outline flex-1">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Dispute modal ─────────────────────────────────────────────────────────────

function DisputeModal({
  escrow,
  onClose,
}: {
  escrow: EscrowTransaction;
  onClose: () => void;
}) {
  const [form, setForm] = useState({ reason: "", details: "" });
  const disputeMut = useRaiseDispute();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await disputeMut.mutateAsync({
      order_id: escrow.order_id,
      reason: form.reason,
      details: form.details || undefined,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="bg-red-600 px-5 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-white font-bold">⚖️ Raise a Dispute</h3>
            <p className="text-red-200 text-xs mt-0.5">Order #{escrow.order_id} · ${escrow.amount_usd}</p>
          </div>
          <button onClick={onClose} className="text-red-200 hover:text-white text-xl">✕</button>
        </div>

        {disputeMut.isSuccess ? (
          <div className="p-6 text-center space-y-4">
            <div className="text-5xl">⚖️</div>
            <h4 className="font-bold text-red-700 text-lg">Dispute Raised</h4>
            <p className="text-gray-500 text-sm">
              Your dispute has been submitted. An AI analysis will be prepared and reviewed by our team within 24–48 hours.
            </p>
            <button onClick={onClose} className="btn-primary w-full">Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              Funds of <strong>${escrow.amount_usd}</strong> will remain frozen until the dispute is resolved by our admin team with AI assistance.
            </div>
            <div>
              <label className="label">Dispute Reason * (min 10 characters)</label>
              <input className="input text-sm" required placeholder="e.g. Herbs did not match the listed grade..."
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                minLength={10} />
            </div>
            <div>
              <label className="label">Additional Details</label>
              <textarea className="input min-h-24 resize-none text-sm"
                placeholder="Describe what happened, what was promised, and what was actually delivered..."
                value={form.details}
                onChange={(e) => setForm({ ...form, details: e.target.value })} />
            </div>
            {disputeMut.isError && (
              <p className="text-red-600 text-sm">⚠️ Failed to raise dispute. Please try again.</p>
            )}
            <div className="flex gap-3">
              <button type="submit" className="bg-red-600 hover:bg-red-700 text-white font-semibold px-5 py-2.5 rounded-lg flex-1 transition-colors"
                disabled={disputeMut.isPending || form.reason.length < 10}>
                {disputeMut.isPending ? <Spinner /> : "⚖️ Submit Dispute"}
              </button>
              <button type="button" onClick={onClose} className="btn-outline flex-1">Cancel</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ── Admin: Resolve dispute ───────────────────────────────────────────────────

function ResolveDisputePanel({ dispute }: { dispute: DisputeListItem }) {
  const [form, setForm] = useState({
    resolution: "release_to_seller" as "release_to_seller" | "refund_to_buyer" | "split_settlement",
    notes: "",
    compensation: "",
  });
  const resolveMut = useResolveDispute();
  const [done, setDone] = useState(false);

  async function handleResolve(e: React.FormEvent) {
    e.preventDefault();
    await resolveMut.mutateAsync({
      escrow_id: dispute.escrow_id,
      resolution: form.resolution,
      resolution_notes: form.notes,
      compensation_amount_usd: form.resolution === "split_settlement" && form.compensation
        ? Number(form.compensation) : undefined,
    });
    setDone(true);
  }

  if (done) return (
    <div className="bg-forest-50 rounded-xl p-4 border border-forest-200 text-sm text-forest-700">
      ✅ Dispute resolved for Order #{dispute.order_id}
    </div>
  );

  return (
    <form onSubmit={handleResolve} className="space-y-3 bg-white border border-gray-100 rounded-xl p-4">
      <h4 className="font-semibold text-gray-700 text-sm">⚖️ Resolve — Order #{dispute.order_id}</h4>

      {/* AI recommendation */}
      {dispute.ai_recommendation_summary && (
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-xs text-purple-800">
          <p className="font-semibold mb-1">🤖 AI Recommendation</p>
          <p className="leading-relaxed">{dispute.ai_recommendation_summary}</p>
        </div>
      )}

      <div>
        <label className="label text-xs">Resolution *</label>
        <select className="select text-sm" value={form.resolution}
          onChange={(e) => setForm({ ...form, resolution: e.target.value as typeof form.resolution })}>
          <option value="release_to_seller">✅ Release to Seller</option>
          <option value="refund_to_buyer">↩️ Refund to Buyer</option>
          <option value="split_settlement">🤝 Split Settlement</option>
        </select>
      </div>

      {form.resolution === "split_settlement" && (
        <div>
          <label className="label text-xs">Buyer compensation (USD)</label>
          <input className="input text-sm" type="number" step="0.01"
            placeholder={`Max: $${dispute.amount_usd}`}
            value={form.compensation}
            onChange={(e) => setForm({ ...form, compensation: e.target.value })} />
        </div>
      )}

      <div>
        <label className="label text-xs">Resolution Notes * (min 10 chars)</label>
        <textarea className="input min-h-16 resize-none text-sm"
          required minLength={10}
          placeholder="Admin notes explaining the decision..."
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })} />
      </div>

      <button type="submit" className="btn-primary w-full text-sm"
        disabled={resolveMut.isPending || form.notes.length < 10}>
        {resolveMut.isPending ? <Spinner /> : "Confirm Resolution →"}
      </button>
    </form>
  );
}

// ── Transaction card ──────────────────────────────────────────────────────────

function TransactionCard({
  tx,
  onRelease,
  onDispute,
}: {
  tx: EscrowTransaction;
  onRelease: () => void;
  onDispute: () => void;
}) {
  const canRelease = tx.status === "held" || tx.status === "delivery_confirmed";
  const canDispute = tx.status === "delivery_confirmed";
  const isDisputable = canDispute;

  const autoReleaseDate = tx.auto_release_at ? new Date(tx.auto_release_at) : null;
  const now = new Date();
  const daysLeft = autoReleaseDate
    ? Math.max(0, Math.ceil((autoReleaseDate.getTime() - now.getTime()) / 86400000))
    : null;

  return (
    <div className="bg-white rounded-xl border border-gray-100 hover:border-forest-200 hover:shadow-sm transition-all p-5">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="font-bold text-gray-800">Order #{tx.order_id}</p>
          <p className="text-xs text-gray-400 mt-0.5">Escrow #{tx.id} · {tx.gateway ?? "Unknown gateway"}</p>
        </div>
        <StatusBadge status={tx.status} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
        <div className="bg-forest-50 rounded-lg p-2.5 text-center">
          <p className="text-xs text-gray-400">Amount</p>
          <p className="font-bold text-forest-700">${Number(tx.amount_usd).toFixed(2)}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-2.5 text-center">
          <p className="text-xs text-gray-400">Held since</p>
          <p className="font-semibold text-gray-700 text-xs">
            {new Date(tx.held_at).toLocaleDateString("en-NG", {
              day: "numeric", month: "short", year: "numeric",
            })}
          </p>
        </div>
        {daysLeft !== null && tx.status === "held" && (
          <div className={`rounded-lg p-2.5 text-center ${daysLeft <= 1 ? "bg-amber-50" : "bg-gray-50"}`}>
            <p className="text-xs text-gray-400">Auto-release in</p>
            <p className={`font-bold text-sm ${daysLeft <= 1 ? "text-amber-600" : "text-gray-700"}`}>
              {daysLeft} day{daysLeft !== 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>

      {/* Dispute info */}
      {tx.dispute_reason && (
        <div className="bg-red-50 border border-red-100 rounded-lg p-3 mb-3 text-xs">
          <p className="font-medium text-red-700 mb-0.5">⚖️ Dispute: {tx.dispute_reason}</p>
          {tx.dispute_raised_at && (
            <p className="text-red-500">
              Raised: {new Date(tx.dispute_raised_at).toLocaleDateString("en-NG", { day: "numeric", month: "short" })}
            </p>
          )}
        </div>
      )}

      {/* Release condition */}
      {tx.release_condition && (
        <p className="text-xs text-gray-500 mb-3">📝 {tx.release_condition}</p>
      )}

      {/* Actions */}
      <div className="flex gap-2 pt-3 border-t border-gray-50">
        {canRelease && tx.status === "held" && (
          <button onClick={onRelease} className="btn-primary text-xs py-1.5 flex-1">
            ✅ Confirm Delivery
          </button>
        )}
        {isDisputable && (
          <button onClick={onDispute}
            className="text-xs py-1.5 flex-1 border-2 border-red-300 text-red-600 hover:bg-red-50 rounded-lg font-semibold transition-colors">
            ⚖️ Raise Dispute
          </button>
        )}
        {(tx.status === "released" || tx.status === "auto_released" || tx.status === "refunded") && (
          <div className="flex-1 text-center text-xs text-gray-400 py-1.5">
            {STATUS_CONFIG[tx.status].icon} Transaction complete
          </div>
        )}
        {tx.status === "disputed" && !tx.dispute_resolved_at && (
          <div className="flex-1 text-center text-xs text-amber-600 py-1.5">
            ⚖️ Under review by admin
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function EscrowDashboard() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const { data: myTxData, isLoading, isError } = useMyEscrowTransactions();
  const { data: disputesData, isLoading: disputesLoading } = useDisputes();

  const [releaseTarget, setReleaseTarget] = useState<EscrowTransaction | null>(null);
  const [disputeTarget, setDisputeTarget] = useState<EscrowTransaction | null>(null);
  const [statusFilter, setStatusFilter] = useState<EscrowStatus | "">("");
  const [activeTab, setActiveTab] = useState<"transactions" | "disputes">("transactions");

  const transactions = myTxData?.transactions ?? [];
  const filtered = statusFilter
    ? transactions.filter((t) => t.status === statusFilter)
    : transactions;

  // Stats
  const held = transactions.filter((t) => t.status === "held").length;
  const released = transactions.filter((t) => t.status === "released" || t.status === "auto_released").length;
  const disputed = transactions.filter((t) => t.status === "disputed").length;
  const totalHeld = transactions
    .filter((t) => t.status === "held" || t.status === "delivery_confirmed")
    .reduce((s, t) => s + Number(t.amount_usd), 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-6 rounded-2xl">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <span>🔒</span> Escrow Dashboard
        </h1>
        <p className="text-forest-100 text-sm mt-1">
          Secure buyer-seller payment escrow — funds released only on confirmed delivery
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Funds Held", value: `$${totalHeld.toFixed(0)}`, icon: "🔒", color: "text-blue-700" },
          { label: "Active Holds", value: held, icon: "⏳", color: "text-amber-700" },
          { label: "Released", value: released, icon: "✅", color: "text-forest-700" },
          { label: "Disputed", value: disputed, icon: "⚖️", color: "text-red-700" },
        ].map((s) => (
          <div key={s.label} className="card py-4 text-center">
            <div className="text-2xl mb-1">{s.icon}</div>
            <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab("transactions")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === "transactions" ? "bg-white text-forest-700 shadow-sm" : "text-gray-500 hover:text-gray-700"
          }`}
        >
          My Transactions ({myTxData?.count ?? 0})
        </button>
        {isAdmin && (
          <button
            onClick={() => setActiveTab("disputes")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeTab === "disputes" ? "bg-white text-red-700 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            ⚖️ Disputes ({disputesData?.count ?? 0})
          </button>
        )}
      </div>

      {/* Transactions tab */}
      {activeTab === "transactions" && (
        <>
          {/* Filters */}
          <div className="card py-3">
            <div className="flex gap-2 flex-wrap items-center">
              <span className="text-sm font-medium text-gray-500">Filter by status:</span>
              {(["", "held", "delivery_confirmed", "released", "disputed", "refunded", "auto_released"] as const).map((s) => (
                <button
                  key={s || "all"}
                  onClick={() => setStatusFilter(s)}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    statusFilter === s
                      ? "bg-forest-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {s ? `${STATUS_CONFIG[s]?.icon} ${STATUS_CONFIG[s]?.label}` : "All"}
                </button>
              ))}
            </div>
          </div>

          {isLoading && <div className="flex justify-center py-12"><Spinner className="w-8 h-8" /></div>}
          {isError && <PageError message="Failed to load escrow transactions." />}
          {!isLoading && filtered.length === 0 && (
            <Empty icon="🔒" title="No escrow transactions"
              subtitle="Your escrow payments will appear here once you initiate a trade." />
          )}
          {!isLoading && filtered.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((tx) => (
                <TransactionCard
                  key={tx.id}
                  tx={tx}
                  onRelease={() => setReleaseTarget(tx)}
                  onDispute={() => setDisputeTarget(tx)}
                />
              ))}
            </div>
          )}
        </>
      )}

      {/* Admin disputes tab */}
      {activeTab === "disputes" && isAdmin && (
        <div className="space-y-4">
          {disputesLoading && <div className="flex justify-center py-8"><Spinner /></div>}
          {!disputesLoading && (!disputesData || disputesData.disputes.length === 0) && (
            <Empty icon="⚖️" title="No active disputes" subtitle="All trade disputes will appear here." />
          )}
          {!disputesLoading && disputesData && disputesData.disputes.length > 0 && (
            <div className="space-y-5">
              {disputesData.disputes.map((dispute) => (
                <div key={dispute.escrow_id} className="card border-red-200">
                  <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
                    <div>
                      <p className="font-bold text-gray-800">Order #{dispute.order_id}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        Escrow #{dispute.escrow_id} · {dispute.gateway ?? "—"}
                      </p>
                      {dispute.dispute_raised_at && (
                        <p className="text-xs text-red-500 mt-0.5">
                          Raised: {new Date(dispute.dispute_raised_at).toLocaleDateString("en-NG", {
                            day: "numeric", month: "short", year: "numeric",
                          })}
                        </p>
                      )}
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-gray-800 text-lg">${Number(dispute.amount_usd).toFixed(2)}</p>
                      <StatusBadge status={dispute.status} />
                    </div>
                  </div>

                  {dispute.dispute_reason && (
                    <div className="bg-red-50 border border-red-100 rounded-lg p-3 mb-4 text-sm">
                      <p className="font-medium text-red-700 mb-1">Dispute Reason</p>
                      <p className="text-red-600">{dispute.dispute_reason}</p>
                    </div>
                  )}

                  {!dispute.dispute_resolved_at && (
                    <ResolveDisputePanel dispute={dispute} />
                  )}

                  {dispute.dispute_resolved_at && (
                    <div className="bg-forest-50 border border-forest-200 rounded-lg p-3 text-sm text-forest-700">
                      ✅ Resolved on {new Date(dispute.dispute_resolved_at).toLocaleDateString("en-NG", {
                        day: "numeric", month: "short", year: "numeric",
                      })}
                      {dispute.resolution_notes && (
                        <p className="text-gray-500 mt-1 text-xs">{dispute.resolution_notes}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {releaseTarget && (
        <ReleaseModal escrow={releaseTarget} onClose={() => setReleaseTarget(null)} />
      )}
      {disputeTarget && (
        <DisputeModal escrow={disputeTarget} onClose={() => setDisputeTarget(null)} />
      )}
    </div>
  );
}
