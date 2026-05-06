import { useState } from "react";
import { useMyShipments, useShipmentDetail } from "../../hooks/useLogistics";
import type { Shipment, ShipmentEvent, TemperatureReading } from "../../hooks/useLogistics";
import { Spinner, Empty, PageError } from "../../components/Layout";
import { Link } from "react-router-dom";

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  pending:        { label: "Pending",       color: "bg-gray-100 text-gray-600",      icon: "⏳" },
  in_transit:     { label: "In Transit",    color: "bg-blue-100 text-blue-700",      icon: "🚚" },
  customs_hold:   { label: "Customs Hold",  color: "bg-amber-100 text-amber-700",    icon: "🛃" },
  delivered:      { label: "Delivered",     color: "bg-forest-100 text-forest-700",  icon: "✅" },
  returned:       { label: "Returned",      color: "bg-red-100 text-red-700",        icon: "↩️" },
};

function EventTypeIcon({ type }: { type: string }) {
  const map: Record<string, string> = {
    departed:     "🛫",
    arrived:      "🛬",
    customs_hold: "🛃",
    in_transit:   "🚚",
    delivered:    "✅",
    out_for_delivery: "🏠",
    exception:    "⚠️",
  };
  const lower = type.toLowerCase().replace(/\s+/g, "_");
  return <span>{map[lower] ?? "📍"}</span>;
}

// ── Mini temperature chart (pure SVG) ────────────────────────────────────────

function TemperatureChart({ readings }: { readings: TemperatureReading[] }) {
  if (!readings.length) return null;

  const W = 500, H = 120;
  const PAD = { t: 16, r: 20, b: 28, l: 40 };
  const cw = W - PAD.l - PAD.r;
  const ch = H - PAD.t - PAD.b;

  const temps = readings.map((r) => r.celsius);
  const minT = Math.min(...temps) - 2;
  const maxT = Math.max(...temps) + 2;
  const range = maxT - minT || 1;

  const xs = readings.map((_, i) => PAD.l + (i / Math.max(readings.length - 1, 1)) * cw);
  const ys = readings.map((r) => PAD.t + ch - ((r.celsius - minT) / range) * ch);

  const pathD = readings.map((_, i) => `${i === 0 ? "M" : "L"} ${xs[i].toFixed(1)} ${ys[i].toFixed(1)}`).join(" ");

  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-gray-500 mb-2 flex items-center gap-1">
        🌡️ Temperature Log (cold chain)
        {readings.some((r) => r.alert) && (
          <span className="badge-red ml-1">⚠️ Alerts</span>
        )}
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-28 border border-gray-100 rounded-lg bg-gray-50">
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((f) => {
          const y = PAD.t + ch * (1 - f);
          const temp = (minT + range * f).toFixed(0);
          return (
            <g key={f}>
              <line x1={PAD.l} y1={y} x2={W - PAD.r} y2={y} stroke="#e5e7eb" strokeWidth="1" />
              <text x={PAD.l - 4} y={y + 4} fontSize="8" fill="#9ca3af" textAnchor="end">{temp}°</text>
            </g>
          );
        })}
        {/* Line */}
        <path d={pathD} fill="none" stroke="#2d7a5e" strokeWidth="2" strokeLinejoin="round" />
        {/* Dots */}
        {readings.map((r, i) => (
          <circle
            key={i}
            cx={xs[i]}
            cy={ys[i]}
            r="3"
            fill={r.alert ? "#ef4444" : "#2d7a5e"}
          />
        ))}
      </svg>
    </div>
  );
}

// ── Timeline ──────────────────────────────────────────────────────────────────

function EventTimeline({ events }: { events: ShipmentEvent[] }) {
  const sorted = [...events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className="space-y-0">
      {sorted.map((ev, i) => (
        <div key={ev.id} className="flex gap-3">
          {/* Line + dot */}
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 rounded-full bg-forest-100 border-2 border-forest-400 flex items-center justify-center text-sm flex-shrink-0">
              <EventTypeIcon type={ev.event_type} />
            </div>
            {i < sorted.length - 1 && (
              <div className="w-0.5 bg-forest-200 flex-1 min-h-6 my-1" />
            )}
          </div>
          <div className="pb-4 flex-1">
            <p className="font-medium text-gray-800 text-sm capitalize">
              {ev.event_type.replace(/_/g, " ")}
            </p>
            {ev.location && (
              <p className="text-xs text-gray-500">📍 {ev.location}</p>
            )}
            {ev.description && (
              <p className="text-xs text-gray-600 mt-0.5">{ev.description}</p>
            )}
            <p className="text-xs text-gray-400 mt-0.5">
              {new Date(ev.timestamp).toLocaleString("en-NG", {
                day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
              })}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Alert settings panel ──────────────────────────────────────────────────────

function AlertSettings({ shipment }: { shipment: Shipment }) {
  const [alerts, setAlerts] = useState({
    customs_hold: true,
    delivered: true,
    temperature: shipment.is_cold_chain,
    delay: true,
  });

  return (
    <div className="space-y-2">
      {[
        { key: "customs_hold" as const, label: "Customs Hold", icon: "🛃" },
        { key: "delivered" as const, label: "Delivered", icon: "✅" },
        { key: "temperature" as const, label: "Temperature Alert (cold chain)", icon: "🌡️" },
        { key: "delay" as const, label: "Delay Warning", icon: "⏰" },
      ].map(({ key, label, icon }) => (
        <label key={key} className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="w-4 h-4 accent-forest-600"
            checked={alerts[key]}
            onChange={(e) => setAlerts({ ...alerts, [key]: e.target.checked })}
          />
          <span className="text-sm text-gray-700">{icon} {label}</span>
        </label>
      ))}
      <button className="btn-outline text-xs py-1.5 mt-2 w-full">Save Alert Preferences</button>
    </div>
  );
}

// ── Shipment list card ────────────────────────────────────────────────────────

function ShipmentListCard({
  shipment,
  active,
  onSelect,
}: {
  shipment: Shipment;
  active: boolean;
  onSelect: () => void;
}) {
  const cfg = STATUS_CONFIG[shipment.status] ?? { label: shipment.status, color: "bg-gray-100 text-gray-600", icon: "📦" };
  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
        active
          ? "border-forest-500 bg-forest-50"
          : "border-gray-100 bg-white hover:border-gray-200"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-gray-800 text-sm truncate">{shipment.tracking_number}</p>
          <p className="text-xs text-gray-400 mt-0.5">Order #{shipment.order_id}</p>
        </div>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${cfg.color}`}>
          {cfg.icon} {cfg.label}
        </span>
      </div>
      <div className="mt-2 text-xs text-gray-500">
        <span>{shipment.origin_state}, NG</span>
        <span className="mx-1.5">→</span>
        <span>{shipment.destination_country}</span>
      </div>
      {shipment.carrier && (
        <p className="text-xs text-gray-400 mt-1">Carrier: {shipment.carrier}</p>
      )}
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ShipmentTracker() {
  const { data: shipments, isLoading, isError } = useMyShipments();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: detail, isFetching } = useShipmentDetail(selectedId ?? 0);

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;
  if (isError) return <PageError message="Failed to load shipments." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-5 rounded-2xl flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <span>🚚</span> Shipment Tracker
          </h1>
          <p className="text-forest-100 text-sm mt-1">Live tracking for all your export shipments</p>
        </div>
        <Link to="/logistics/documents" className="btn-outline border-white text-white hover:bg-white/10 text-sm">
          📂 Document Vault
        </Link>
      </div>

      {(!shipments || shipments.length === 0) ? (
        <Empty icon="🚢" title="No active shipments"
          subtitle="Your export shipments will appear here once orders are placed." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* List */}
          <div className="lg:col-span-1 space-y-2">
            <p className="text-sm font-medium text-gray-500 mb-3">
              {shipments.length} shipment{shipments.length > 1 ? "s" : ""}
            </p>
            {shipments.map((s) => (
              <ShipmentListCard
                key={s.id}
                shipment={s}
                active={selectedId === s.id}
                onSelect={() => setSelectedId(s.id)}
              />
            ))}
          </div>

          {/* Detail */}
          <div className="lg:col-span-2">
            {!selectedId ? (
              <div className="card text-center py-16 text-gray-400">
                <p className="text-3xl mb-3">👈</p>
                <p className="font-medium">Select a shipment to view details</p>
              </div>
            ) : isFetching && !detail ? (
              <div className="card flex justify-center py-16"><Spinner /></div>
            ) : detail ? (
              <div className="space-y-4">
                {/* Header */}
                <div className="card">
                  <div className="flex items-start justify-between flex-wrap gap-3">
                    <div>
                      <h2 className="font-bold text-gray-800 text-lg">{detail.tracking_number}</h2>
                      <p className="text-sm text-gray-500">Order #{detail.order_id} · {detail.carrier ?? "Unknown carrier"}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      STATUS_CONFIG[detail.status]?.color ?? "bg-gray-100 text-gray-600"
                    }`}>
                      {STATUS_CONFIG[detail.status]?.icon} {STATUS_CONFIG[detail.status]?.label ?? detail.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-gray-100">
                    {[
                      { label: "Route", value: `${detail.origin_state} → ${detail.destination_country}` },
                      { label: "Channel", value: detail.freight_channel },
                      { label: "Weight", value: detail.weight_kg ? `${detail.weight_kg} kg` : "—" },
                      { label: "Est. Delivery", value: detail.estimated_delivery
                          ? new Date(detail.estimated_delivery).toLocaleDateString("en-NG", { day: "numeric", month: "short" })
                          : "—" },
                    ].map((item) => (
                      <div key={item.label}>
                        <p className="text-xs text-gray-400 mb-0.5">{item.label}</p>
                        <p className="font-semibold text-gray-800 text-sm capitalize">{item.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Temperature chart */}
                  {detail.is_cold_chain && detail.temperature_log && (
                    <TemperatureChart readings={detail.temperature_log} />
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Timeline */}
                  <div className="sm:col-span-2 card">
                    <h3 className="font-bold text-gray-800 mb-4">📍 Tracking Timeline</h3>
                    {detail.events.length === 0 ? (
                      <p className="text-sm text-gray-400">No tracking events yet.</p>
                    ) : (
                      <EventTimeline events={detail.events} />
                    )}
                  </div>

                  {/* Sidebar */}
                  <div className="space-y-4">
                    {/* Documents */}
                    <div className="card">
                      <h3 className="font-bold text-gray-800 mb-3 text-sm">📂 Documents</h3>
                      {detail.documents.length === 0 ? (
                        <p className="text-xs text-gray-400">No documents attached.</p>
                      ) : (
                        <div className="space-y-1.5">
                          {detail.documents.map((doc) => (
                            <div key={doc.id} className="flex items-center justify-between">
                              <p className="text-xs text-gray-700 capitalize">
                                {doc.document_type.replace(/_/g, " ")}
                              </p>
                              {doc.file_url ? (
                                <a href={doc.file_url} target="_blank" rel="noreferrer"
                                  className="text-xs text-forest-600 hover:text-forest-800">
                                  ↓ PDF
                                </a>
                              ) : (
                                <span className="text-xs text-gray-300">Pending</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                      <Link to={`/logistics/documents?order_id=${detail.order_id}`}
                        className="text-xs text-forest-600 hover:text-forest-800 font-medium mt-2 block">
                        Manage documents →
                      </Link>
                    </div>

                    {/* Alert settings */}
                    <div className="card">
                      <h3 className="font-bold text-gray-800 mb-3 text-sm">🔔 Alert Settings</h3>
                      <AlertSettings shipment={detail} />
                    </div>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
