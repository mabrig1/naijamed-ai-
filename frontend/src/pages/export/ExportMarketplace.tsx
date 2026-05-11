import { useState } from "react";
import { Link } from "react-router-dom";
import { useExportListings, useSendTradeInquiry } from "../../hooks/useExport";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { ExportListing } from "../../hooks/useExport";

// ── Trust badges (placeholder SVG) ───────────────────────────────────────────

function NAFDACBadge() {
  return (
    <svg viewBox="0 0 48 20" className="h-5" aria-label="NAFDAC Certified">
      <rect width="48" height="20" rx="3" fill="#008751" />
      <text x="24" y="14" textAnchor="middle" fill="white" fontSize="7" fontWeight="bold" fontFamily="Arial">NAFDAC</text>
    </svg>
  );
}

function NEPCBadge() {
  return (
    <svg viewBox="0 0 44 20" className="h-5" aria-label="NEPC Registered">
      <rect width="44" height="20" rx="3" fill="#D4A017" />
      <text x="22" y="14" textAnchor="middle" fill="#1B4332" fontSize="7" fontWeight="bold" fontFamily="Arial">NEPC</text>
    </svg>
  );
}

function NAQSBadge() {
  return (
    <svg viewBox="0 0 44 20" className="h-5" aria-label="NAQS Approved">
      <rect width="44" height="20" rx="3" fill="#163828" />
      <text x="22" y="14" textAnchor="middle" fill="white" fontSize="7" fontWeight="bold" fontFamily="Arial">NAQS</text>
    </svg>
  );
}

// ── Stars ──────────────────────────────────────────────────────────────────

function StarRating({ rating }: { rating: number | null }) {
  if (!rating) return <span className="text-xs text-gray-400">No rating</span>;
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <span key={s} className={s <= Math.round(rating) ? "text-gold-400 text-xs" : "text-gray-300 text-xs"}>★</span>
      ))}
      <span className="text-xs text-gray-500 ml-1">{rating.toFixed(1)}</span>
    </span>
  );
}

// ── Grade badge ───────────────────────────────────────────────────────────────

function GradeBadge({ grade }: { grade: string }) {
  const map: Record<string, string> = {
    A: "bg-forest-100 text-forest-700",
    B: "bg-blue-100 text-blue-700",
    C: "bg-gray-100 text-gray-600",
    organic: "bg-green-100 text-green-700",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${map[grade] ?? "bg-gray-100 text-gray-600"}`}>
      {grade === "organic" ? "🌿 Organic" : `Grade ${grade}`}
    </span>
  );
}

// ── Listing card ──────────────────────────────────────────────────────────────

function ListingCard({
  listing,
  onRequestQuote,
}: {
  listing: ExportListing;
  onRequestQuote: (listing: ExportListing) => void;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-forest-100 hover:shadow-md hover:border-forest-300 transition-all duration-200 overflow-hidden flex flex-col">
      {/* Header strip */}
      <div className="bg-gradient-to-r from-forest-600 to-forest-500 px-4 py-3 flex items-center justify-between">
        <div>
          <h3 className="font-bold text-white text-base leading-tight">{listing.herb_name}</h3>
          {listing.scientific_name && (
            <p className="text-forest-200 text-xs italic">{listing.scientific_name}</p>
          )}
        </div>
        <GradeBadge grade={listing.grade} />
      </div>

      <div className="p-4 flex-1 flex flex-col gap-3">
        {/* Price & quantity */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-forest-50 rounded-lg p-2.5 text-center">
            <p className="text-xs text-gray-500 mb-0.5">Price/kg</p>
            <p className="font-bold text-forest-700 text-lg">${listing.price_per_kg_usd.toFixed(2)}</p>
          </div>
          <div className="bg-gold-50 rounded-lg p-2.5 text-center">
            <p className="text-xs text-gray-500 mb-0.5">Available</p>
            <p className="font-bold text-gold-600 text-lg">{listing.quantity_kg.toLocaleString()} kg</p>
          </div>
        </div>

        {/* Origin & destinations */}
        <div className="text-sm space-y-1">
          <div className="flex gap-2">
            <span className="text-gray-400 text-xs">📍</span>
            <span className="text-gray-700 text-xs">{listing.origin_state}, Nigeria</span>
          </div>
          {listing.destination_countries.length > 0 && (
            <div className="flex gap-2">
              <span className="text-gray-400 text-xs">🌍</span>
              <span className="text-gray-600 text-xs">
                Ships to: {listing.destination_countries.slice(0, 3).join(", ")}
                {listing.destination_countries.length > 3 && ` +${listing.destination_countries.length - 3}`}
              </span>
            </div>
          )}
        </div>

        {/* Certification badges */}
        <div className="flex flex-wrap gap-1.5 mt-auto">
          {listing.nafdac_cert_url && <NAFDACBadge />}
          {listing.nepc_cert_url && <NEPCBadge />}
          {listing.naqs_cert_url && <NAQSBadge />}
          {listing.is_organic && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">
              🌿 Organic
            </span>
          )}
        </div>

        {/* Seller rating */}
        <StarRating rating={listing.seller_rating} />

        {/* Freight channels */}
        {listing.freight_channels.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {listing.freight_channels.map((ch) => (
              <span key={ch} className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                {ch === "air" ? "✈️" : ch === "sea" ? "🚢" : ch === "road" ? "🚛" : "📦"} {ch}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="px-4 pb-4 flex gap-2">
        <Link
          to={`/export/listings/${listing.id}`}
          className="btn-outline text-sm py-2 flex-1 text-center"
        >
          View Details
        </Link>
        <button
          onClick={() => onRequestQuote(listing)}
          className="btn-primary text-sm py-2 flex-1"
        >
          📩 Request Quote
        </button>
      </div>
    </div>
  );
}

// ── Inquiry modal ─────────────────────────────────────────────────────────────

function InquiryModal({
  listing,
  onClose,
}: {
  listing: ExportListing;
  onClose: () => void;
}) {
  const [form, setForm] = useState({
    message: "",
    quantity_kg: "",
    target_price_usd: "",
    contact_email: "",
  });
  const inquireMut = useSendTradeInquiry();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await inquireMut.mutateAsync({
      listing_id: listing.id,
      message: form.message,
      quantity_kg: form.quantity_kg ? Number(form.quantity_kg) : undefined,
      target_price_usd: form.target_price_usd ? Number(form.target_price_usd) : undefined,
      contact_email: form.contact_email || undefined,
    });
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        <div className="bg-forest-600 px-6 py-4 flex items-center justify-between">
          <div>
            <h3 className="text-white font-bold text-lg">Request Quote</h3>
            <p className="text-forest-200 text-sm">{listing.herb_name} — Grade {listing.grade}</p>
          </div>
          <button onClick={onClose} className="text-forest-200 hover:text-white text-xl">✕</button>
        </div>

        {inquireMut.isSuccess ? (
          <div className="p-6 text-center space-y-4">
            <div className="text-5xl">✅</div>
            <h4 className="font-bold text-forest-700 text-lg">Inquiry Sent!</h4>
            <p className="text-gray-500 text-sm">The seller will respond to your inquiry within 24 hours.</p>
            <button onClick={onClose} className="btn-primary w-full">Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Quantity (kg)</label>
                <input
                  className="input"
                  type="number"
                  placeholder={`Max ${listing.quantity_kg} kg`}
                  value={form.quantity_kg}
                  onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })}
                />
              </div>
              <div>
                <label className="label">Target Price (USD/kg)</label>
                <input
                  className="input"
                  type="number"
                  step="0.01"
                  placeholder={`List: $${listing.price_per_kg_usd}`}
                  value={form.target_price_usd}
                  onChange={(e) => setForm({ ...form, target_price_usd: e.target.value })}
                />
              </div>
            </div>
            <div>
              <label className="label">Contact Email</label>
              <input
                className="input"
                type="email"
                placeholder="your@email.com"
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Message *</label>
              <textarea
                className="input min-h-28 resize-none"
                placeholder="Describe your requirements: certification needs, packaging, delivery timeline, incoterms preference..."
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                required
              />
            </div>
            {inquireMut.isError && (
              <p className="text-red-600 text-sm">Failed to send inquiry. Please try again.</p>
            )}
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                className="btn-primary flex-1"
                disabled={inquireMut.isPending || !form.message}
              >
                {inquireMut.isPending ? <Spinner /> : "Send Trade Inquiry →"}
              </button>
              <button type="button" onClick={onClose} className="btn-outline flex-1">Cancel</button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const NIGERIAN_STATES = [
  "Abia","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno",
  "Cross River","Delta","Ebonyi","Edo","Ekiti","Enugu","FCT","Gombe","Imo",
  "Jigawa","Kaduna","Kano","Katsina","Kebbi","Kogi","Kwara","Lagos","Nasarawa",
  "Niger","Ogun","Ondo","Osun","Oyo","Plateau","Rivers","Sokoto","Taraba","Yobe","Zamfara",
];

const DESTINATION_COUNTRIES = [
  "Germany","United Kingdom","United States","France","Netherlands","Canada",
  "UAE","Saudi Arabia","China","Japan","India","Australia",
];

export default function ExportMarketplace() {
  const [filters, setFilters] = useState({
    herb_id: "",
    grade: "",
    country: "",
    is_organic: false,
    min_price: "",
    max_price: "",
    freight_channel: "",
  });
  const [selectedListing, setSelectedListing] = useState<ExportListing | null>(null);

  const { data: herbs } = useHerbList({ limit: 100 });
  const { data: listings, isLoading, isError } = useExportListings({
    herb_id: filters.herb_id ? Number(filters.herb_id) : undefined,
    grade: filters.grade || undefined,
    country: filters.country || undefined,
    is_organic: filters.is_organic || undefined,
    min_price: filters.min_price ? Number(filters.min_price) : undefined,
    max_price: filters.max_price ? Number(filters.max_price) : undefined,
    freight_channel: filters.freight_channel || undefined,
  });

  return (
    <div className="space-y-6">
      {/* Hero — Nigerian flag colours */}
      <div className="relative overflow-hidden rounded-2xl">
        {/* Flag: green | white | green */}
        <div className="absolute inset-0 flex">
          <div className="w-1/3 bg-forest-600" />
          <div className="w-1/3 bg-white" />
          <div className="w-1/3 bg-forest-600" />
        </div>
        <div className="relative bg-forest-700/85 text-white px-6 py-8 sm:py-10">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-3xl">🌿</span>
              <span className="text-gold-300 font-bold text-sm uppercase tracking-widest">NigerFlora Export Hub</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-bold mb-2">
              Nigerian Herb Export Marketplace
            </h1>
            <p className="text-forest-100 text-sm sm:text-base leading-relaxed max-w-xl">
              NAFDAC-certified. NEPC-registered. Trade-ready herbs from verified Nigerian farms — connecting African botanical wealth to global pharmaceutical markets.
            </p>
            {/* Trust badges */}
            <div className="flex items-center gap-3 mt-5 flex-wrap">
              <NAFDACBadge />
              <NEPCBadge />
              <NAQSBadge />
              <span className="text-forest-300 text-xs">|</span>
              <span className="text-xs text-forest-200">Verified certifications on every listing</span>
            </div>
          </div>
          <div className="absolute right-6 top-4 flex gap-2">
            <Link to="/export/create" className="btn-secondary text-sm">
              ➕ List Your Herbs
            </Link>
            <Link to="/export/buyers/register" className="btn-outline border-white text-white hover:bg-white/10 text-sm">
              🌍 Register as Buyer
            </Link>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { icon: "🌿", label: "Active Listings", value: listings?.length ?? "—" },
          { icon: "🌍", label: "Export Countries", value: "47" },
          { icon: "✅", label: "Verified Sellers", value: "200+" },
          { icon: "📦", label: "Tonnes Exported", value: "1,200+" },
        ].map((s) => (
          <div key={s.label} className="card text-center py-3">
            <div className="text-2xl mb-1">{s.icon}</div>
            <div className="text-xl font-bold text-forest-700">{s.value}</div>
            <div className="text-xs text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="card">
        <h2 className="font-semibold text-gray-700 mb-4 flex items-center gap-2">
          <span>🔍</span> Filter Listings
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          <div>
            <label className="label">Herb Type</label>
            <select className="select" value={filters.herb_id}
              onChange={(e) => setFilters({ ...filters, herb_id: e.target.value })}>
              <option value="">All herbs</option>
              {herbs?.map((h) => <option key={h.id} value={h.id}>{h.name_english}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Grade</label>
            <select className="select" value={filters.grade}
              onChange={(e) => setFilters({ ...filters, grade: e.target.value })}>
              <option value="">Any grade</option>
              <option value="A">Grade A</option>
              <option value="B">Grade B</option>
              <option value="C">Grade C</option>
              <option value="organic">Organic</option>
            </select>
          </div>
          <div>
            <label className="label">Destination Country</label>
            <select className="select" value={filters.country}
              onChange={(e) => setFilters({ ...filters, country: e.target.value })}>
              <option value="">Any country</option>
              {DESTINATION_COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Freight Channel</label>
            <select className="select" value={filters.freight_channel}
              onChange={(e) => setFilters({ ...filters, freight_channel: e.target.value })}>
              <option value="">Any channel</option>
              <option value="air">✈️ Air</option>
              <option value="sea">🚢 Sea</option>
              <option value="road">🚛 Road</option>
              <option value="ecommerce">📦 E-Commerce</option>
            </select>
          </div>
          <div>
            <label className="label">Min Price (USD/kg)</label>
            <input className="input" type="number" step="0.01" placeholder="0.00"
              value={filters.min_price}
              onChange={(e) => setFilters({ ...filters, min_price: e.target.value })} />
          </div>
          <div>
            <label className="label">Max Price (USD/kg)</label>
            <input className="input" type="number" step="0.01" placeholder="Any"
              value={filters.max_price}
              onChange={(e) => setFilters({ ...filters, max_price: e.target.value })} />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 rounded accent-forest-600"
                checked={filters.is_organic}
                onChange={(e) => setFilters({ ...filters, is_organic: e.target.checked })}
              />
              <span className="text-sm font-medium text-gray-700">🌿 Organic only</span>
            </label>
          </div>
          <div className="flex items-end">
            <button
              onClick={() => setFilters({ herb_id: "", grade: "", country: "", is_organic: false, min_price: "", max_price: "", freight_channel: "" })}
              className="btn-ghost text-sm w-full"
            >
              ✕ Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading && (
        <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>
      )}
      {isError && <PageError message="Failed to load export listings. Please try again." />}
      {!isLoading && listings?.length === 0 && (
        <Empty icon="🌿" title="No listings match your filters"
          subtitle="Try broadening your search or check back later for new listings." />
      )}
      {!isLoading && listings && listings.length > 0 && (
        <>
          <p className="text-sm text-gray-500">{listings.length} listings found</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {listings.map((l) => (
              <ListingCard key={l.id} listing={l} onRequestQuote={setSelectedListing} />
            ))}
          </div>
        </>
      )}

      {/* Inquiry modal */}
      {selectedListing && (
        <InquiryModal listing={selectedListing} onClose={() => setSelectedListing(null)} />
      )}
    </div>
  );
}
