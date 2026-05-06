import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useExportListingDetail, useSendTradeInquiry, useCalculateFreight } from "../../hooks/useExport";
import type { FreightOption } from "../../hooks/useExport";
import { Spinner, PageError } from "../../components/Layout";

function NAFDACBadge() {
  return (
    <svg viewBox="0 0 56 22" className="h-5">
      <rect width="56" height="22" rx="3" fill="#008751"/>
      <text x="28" y="15" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold" fontFamily="Arial">NAFDAC</text>
    </svg>
  );
}
function NEPCBadge() {
  return (
    <svg viewBox="0 0 48 22" className="h-5">
      <rect width="48" height="22" rx="3" fill="#D4A017"/>
      <text x="24" y="15" textAnchor="middle" fill="#1B4332" fontSize="8" fontWeight="bold" fontFamily="Arial">NEPC</text>
    </svg>
  );
}
function NAQSBadge() {
  return (
    <svg viewBox="0 0 48 22" className="h-5">
      <rect width="48" height="22" rx="3" fill="#163828"/>
      <text x="24" y="15" textAnchor="middle" fill="white" fontSize="8" fontWeight="bold" fontFamily="Arial">NAQS</text>
    </svg>
  );
}

function FreightCard({ channel, option, recommended }: {
  channel: string; option: FreightOption; recommended: boolean;
}) {
  const icons: Record<string, string> = { air: "✈️", sea: "🚢", road: "🚛", ecommerce: "📦" };
  return (
    <div className={`rounded-xl border-2 p-4 relative transition-all ${
      recommended
        ? "border-forest-500 bg-forest-50 shadow-md"
        : "border-gray-200 bg-white"
    }`}>
      {recommended && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-forest-600 text-white text-xs font-bold px-3 py-1 rounded-full">
            🤖 AI Recommended
          </span>
        </div>
      )}
      <div className="text-center mb-3 mt-1">
        <span className="text-2xl">{icons[channel] ?? "📦"}</span>
        <p className="font-bold text-gray-700 capitalize mt-1">{channel}</p>
        <p className="text-2xl font-bold text-forest-700 mt-1">${option.total_usd.toFixed(0)}</p>
        <p className="text-xs text-gray-400">total USD</p>
      </div>
      <div className="space-y-1 text-xs text-gray-600">
        <div className="flex justify-between">
          <span>Freight</span><span>${option.freight_usd.toFixed(0)}</span>
        </div>
        <div className="flex justify-between">
          <span>Insurance</span><span>${option.insurance_usd.toFixed(0)}</span>
        </div>
        <div className="flex justify-between">
          <span>Handling</span><span>${option.handling_usd.toFixed(0)}</span>
        </div>
        <div className="flex justify-between border-t border-gray-100 pt-1 font-medium">
          <span>Transit time</span><span>{option.transit_days} days</span>
        </div>
      </div>
      {option.notes && (
        <p className="text-xs text-gray-400 mt-2 italic">{option.notes}</p>
      )}
    </div>
  );
}

export default function ExportListingDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: listing, isLoading, isError } = useExportListingDetail(Number(id));
  const inquireMut = useSendTradeInquiry();
  const freightMut = useCalculateFreight();

  const [showInquiry, setShowInquiry] = useState(false);
  const [inquiryForm, setInquiryForm] = useState({ message: "", quantity_kg: "", contact_email: "" });
  const [freightQty, setFreightQty] = useState("");
  const [freightDest, setFreightDest] = useState("");

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;
  if (isError || !listing) return <PageError message="Listing not found or unavailable." />;

  const freightData = freightMut.data;

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/export" className="hover:text-forest-600">Export Marketplace</Link>
        <span>›</span>
        <span className="text-gray-700">{listing.herb_name}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content — left 2/3 */}
        <div className="lg:col-span-2 space-y-5">

          {/* Hero card */}
          <div className="card">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  {listing.status === "active" && (
                    <span className="badge-green">● Active</span>
                  )}
                  {listing.is_organic && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
                      🌿 Organic
                    </span>
                  )}
                </div>
                <h1 className="text-2xl font-bold text-gray-900">{listing.herb_name}</h1>
                {listing.scientific_name && (
                  <p className="text-gray-400 italic text-sm">{listing.scientific_name}</p>
                )}
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-forest-700">${listing.price_per_kg_usd.toFixed(2)}</p>
                <p className="text-gray-400 text-sm">per kg USD</p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4 border-y border-gray-100">
              {[
                { label: "Grade", value: listing.grade },
                { label: "Available", value: `${listing.quantity_kg.toLocaleString()} kg` },
                { label: "Origin", value: `${listing.origin_state}, NG` },
                { label: "HS Code", value: listing.hs_code ?? "N/A" },
              ].map((item) => (
                <div key={item.label} className="text-center">
                  <p className="text-xs text-gray-400 mb-0.5">{item.label}</p>
                  <p className="font-bold text-gray-800">{item.value}</p>
                </div>
              ))}
            </div>

            {listing.description && (
              <p className="text-gray-600 text-sm mt-4 leading-relaxed">{listing.description}</p>
            )}

            {/* Certification badges */}
            <div className="flex gap-2 flex-wrap mt-4">
              {listing.nafdac_cert_url && <NAFDACBadge />}
              {listing.nepc_cert_url && <NEPCBadge />}
              {listing.naqs_cert_url && <NAQSBadge />}
            </div>
          </div>

          {/* GPS Map placeholder */}
          {listing.gps_lat && listing.gps_lng && (
            <div className="card">
              <h2 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                <span>📍</span> Farm Location
              </h2>
              <div className="bg-forest-50 rounded-xl p-4 border border-forest-100 flex items-center gap-4">
                <div className="text-4xl">🗺️</div>
                <div>
                  <p className="font-medium text-gray-700">{listing.origin_state} State, Nigeria</p>
                  <p className="text-sm text-gray-500">
                    GPS: {listing.gps_lat}° N, {listing.gps_lng}° E
                  </p>
                  <a
                    href={`https://www.google.com/maps?q=${listing.gps_lat},${listing.gps_lng}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-forest-600 hover:text-forest-800 font-medium mt-1 inline-block"
                  >
                    Open in Google Maps →
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* Freight quote calculator */}
          <div className="card">
            <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
              <span>🚢</span> Freight Quote Calculator
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
              <div>
                <label className="label">Destination Country</label>
                <input className="input" placeholder="e.g. Germany"
                  value={freightDest} onChange={(e) => setFreightDest(e.target.value)} />
              </div>
              <div>
                <label className="label">Quantity (kg)</label>
                <input className="input" type="number" min="1" placeholder="e.g. 500"
                  value={freightQty} onChange={(e) => setFreightQty(e.target.value)} />
              </div>
              <div className="flex items-end">
                <button
                  className="btn-primary w-full"
                  disabled={!freightDest || !freightQty || freightMut.isPending}
                  onClick={() =>
                    freightMut.mutate({
                      herb_type: listing.herb_name,
                      origin_state: listing.origin_state,
                      destination_country: freightDest,
                      quantity_kg: Number(freightQty),
                    })
                  }
                >
                  {freightMut.isPending ? <Spinner /> : "Calculate →"}
                </button>
              </div>
            </div>

            {freightData && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                {(["air","sea","road","ecommerce"] as const).map((ch) => {
                  const opt = freightData[ch as keyof typeof freightData] as FreightOption | null;
                  if (!opt) return null;
                  return (
                    <FreightCard
                      key={ch}
                      channel={ch}
                      option={opt}
                      recommended={freightData.ai_recommendation === ch}
                    />
                  );
                })}
              </div>
            )}
            {freightData?.ai_recommendation && (
              <div className="mt-3 p-3 bg-forest-50 border border-forest-200 rounded-lg text-sm text-forest-700">
                🤖 <strong>AI Recommendation:</strong> {freightData.ai_recommendation} freight is optimal for this shipment.
              </div>
            )}
          </div>

          {/* Seller info */}
          <div className="card">
            <h2 className="font-bold text-gray-800 mb-3">👤 Seller Information</h2>
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-forest-100 rounded-full flex items-center justify-center text-forest-700 font-bold text-xl">
                {listing.seller_name?.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-semibold text-gray-800">{listing.seller_name}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  {listing.seller_verified && (
                    <span className="badge-green text-xs">✓ Verified Seller</span>
                  )}
                  {listing.seller_rating && (
                    <span className="text-xs text-gray-500">★ {listing.seller_rating.toFixed(1)}/5</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right sidebar — AI matches & CTA */}
        <div className="space-y-5">

          {/* CTA card */}
          <div className="card border-forest-300 bg-forest-50 space-y-3">
            <div className="text-center py-2">
              <p className="text-2xl font-bold text-forest-700">
                ${listing.price_per_kg_usd.toFixed(2)}
                <span className="text-sm font-normal text-gray-500">/kg</span>
              </p>
              <p className="text-xs text-gray-500 mt-0.5">{listing.quantity_kg.toLocaleString()} kg available</p>
            </div>
            <button
              onClick={() => setShowInquiry(true)}
              className="btn-primary w-full text-base"
            >
              📩 Send Trade Inquiry
            </button>
            <Link to={`/logistics/freight`} className="btn-outline w-full text-center block text-sm">
              🚢 Book Freight
            </Link>
            <Link to={`/escrow/hold?order_id=${listing.id}`} className="btn-ghost w-full text-center block text-sm text-forest-700">
              🔒 Pay via Escrow
            </Link>
          </div>

          {/* Freight channels available */}
          <div className="card">
            <h3 className="font-semibold text-gray-700 mb-2">Available Freight</h3>
            <div className="space-y-1.5">
              {listing.freight_channels.map((ch) => {
                const icons: Record<string, string> = { air: "✈️", sea: "🚢", road: "🚛", ecommerce: "📦" };
                return (
                  <div key={ch} className="flex items-center gap-2 text-sm text-gray-600">
                    <span>{icons[ch] ?? "📦"}</span>
                    <span className="capitalize">{ch} freight</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* AI buyer matches */}
          {listing.ai_buyer_matches && listing.ai_buyer_matches.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span>🤖</span> Matched Buyers
              </h3>
              <div className="space-y-3">
                {listing.ai_buyer_matches.slice(0, 4).map((buyer) => (
                  <div key={buyer.buyer_id} className="flex items-center justify-between border-b border-gray-50 pb-2 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{buyer.buyer_name}</p>
                      <p className="text-xs text-gray-400">{buyer.country} · {buyer.monthly_volume_kg.toLocaleString()} kg/mo</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-bold text-forest-600">{buyer.match_score}%</div>
                      <div className="text-xs text-gray-400">match</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Certifications */}
          <div className="card">
            <h3 className="font-semibold text-gray-700 mb-3">Certifications</h3>
            <div className="space-y-2">
              {listing.nafdac_cert_url && (
                <a href={listing.nafdac_cert_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-2 text-sm text-forest-600 hover:text-forest-800">
                  <NAFDACBadge /> View NAFDAC Certificate
                </a>
              )}
              {listing.nepc_cert_url && (
                <a href={listing.nepc_cert_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-2 text-sm text-gold-600 hover:text-gold-800">
                  <NEPCBadge /> View NEPC Registration
                </a>
              )}
              {listing.naqs_cert_url && (
                <a href={listing.naqs_cert_url} target="_blank" rel="noreferrer"
                  className="flex items-center gap-2 text-sm text-forest-700 hover:text-forest-900">
                  <NAQSBadge /> View NAQS Certificate
                </a>
              )}
              {!listing.nafdac_cert_url && !listing.nepc_cert_url && !listing.naqs_cert_url && (
                <p className="text-xs text-gray-400">No certificates uploaded yet.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Inquiry modal */}
      {showInquiry && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
            <div className="bg-forest-600 px-6 py-4 flex items-center justify-between">
              <div>
                <h3 className="text-white font-bold text-lg">Send Trade Inquiry</h3>
                <p className="text-forest-200 text-sm">{listing.herb_name}</p>
              </div>
              <button onClick={() => setShowInquiry(false)} className="text-forest-200 hover:text-white text-xl">✕</button>
            </div>
            {inquireMut.isSuccess ? (
              <div className="p-6 text-center space-y-4">
                <div className="text-5xl">✅</div>
                <h4 className="font-bold text-forest-700 text-lg">Inquiry Sent!</h4>
                <p className="text-gray-500 text-sm">The seller will respond within 24 hours.</p>
                <button onClick={() => { setShowInquiry(false); inquireMut.reset(); }} className="btn-primary w-full">Close</button>
              </div>
            ) : (
              <form className="p-6 space-y-4" onSubmit={async (e) => {
                e.preventDefault();
                await inquireMut.mutateAsync({
                  listing_id: listing.id,
                  message: inquiryForm.message,
                  quantity_kg: inquiryForm.quantity_kg ? Number(inquiryForm.quantity_kg) : undefined,
                  contact_email: inquiryForm.contact_email || undefined,
                });
              }}>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Quantity (kg)</label>
                    <input className="input" type="number" placeholder="e.g. 500"
                      value={inquiryForm.quantity_kg}
                      onChange={(e) => setInquiryForm({ ...inquiryForm, quantity_kg: e.target.value })} />
                  </div>
                  <div>
                    <label className="label">Your Email</label>
                    <input className="input" type="email" placeholder="you@company.com"
                      value={inquiryForm.contact_email}
                      onChange={(e) => setInquiryForm({ ...inquiryForm, contact_email: e.target.value })} />
                  </div>
                </div>
                <div>
                  <label className="label">Message *</label>
                  <textarea className="input min-h-28 resize-none"
                    placeholder="Describe your requirements..."
                    value={inquiryForm.message}
                    onChange={(e) => setInquiryForm({ ...inquiryForm, message: e.target.value })}
                    required />
                </div>
                <div className="flex gap-3">
                  <button type="submit" className="btn-primary flex-1" disabled={inquireMut.isPending}>
                    {inquireMut.isPending ? <Spinner /> : "Send →"}
                  </button>
                  <button type="button" onClick={() => setShowInquiry(false)} className="btn-outline flex-1">Cancel</button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
