import { useState } from "react";
import { Link } from "react-router-dom";
import { useFarmListings, useInquireListing, useDeleteListing } from "../../hooks/useFarming";
import { useHerbList } from "../../hooks/useHerbs";
import { useAuth } from "../../hooks/useAuth";
import { Spinner, Empty, PageError } from "../../components/Layout";
import type { FarmListing } from "../../types";

function ListingCard({ listing, onInquire, onDelete, canDelete }: {
  listing: FarmListing;
  onInquire: (id: number) => void;
  onDelete: (id: number) => void;
  canDelete: boolean;
}) {
  const qualityColor: Record<string, string> = {
    premium:  "badge-green",
    standard: "bg-blue-100 text-blue-700 text-xs font-medium px-2.5 py-0.5 rounded-full",
    economy:  "bg-gray-100 text-gray-600 text-xs font-medium px-2.5 py-0.5 rounded-full",
    high:     "badge-green",
    medium:   "bg-blue-100 text-blue-700 text-xs font-medium px-2.5 py-0.5 rounded-full",
    low:      "bg-gray-100 text-gray-600 text-xs font-medium px-2.5 py-0.5 rounded-full",
  };

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold text-forest-700 text-lg">{listing.herb?.name_english ?? `Herb #${listing.herb_id}`}</h3>
          {listing.herb?.scientific_name && (
            <p className="text-xs italic text-gray-400">{listing.herb.scientific_name}</p>
          )}
        </div>
        {listing.quality_score && (
          <span className={qualityColor[listing.quality_score] ?? "badge-gray"}>{listing.quality_score}</span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm mb-4">
        <div>
          <span className="text-gray-500">Quantity</span>
          <p className="font-semibold text-gray-800">{listing.quantity_kg} kg</p>
        </div>
        <div>
          <span className="text-gray-500">Price</span>
          <p className="font-semibold text-forest-600">₦{Number(listing.price_per_kg).toLocaleString()}/kg</p>
        </div>
        <div>
          <span className="text-gray-500">Location</span>
          <p className="font-medium text-gray-700">{listing.location}</p>
        </div>
        <div>
          <span className="text-gray-500">Farmer</span>
          <p className="font-medium text-gray-700">{listing.farmer?.full_name ?? "—"}</p>
        </div>
      </div>

      {listing.harvest_date && (
        <p className="text-xs text-gray-400 mb-3">
          Harvested: {new Date(listing.harvest_date).toLocaleDateString("en-NG", { day: "numeric", month: "short", year: "numeric" })}
        </p>
      )}

      <div className="flex gap-2 pt-3 border-t border-gray-100">
        {canDelete ? (
          <button
            onClick={() => onDelete(listing.id)}
            className="btn-outline text-sm py-1.5 border-red-300 text-red-600 hover:bg-red-50 flex-1"
          >
            Delete
          </button>
        ) : (
          <button
            onClick={() => onInquire(listing.id)}
            className="btn-primary text-sm py-1.5 flex-1"
          >
            📩 Inquire
          </button>
        )}
      </div>
    </div>
  );
}

export default function Marketplace() {
  const { user } = useAuth();
  const [herbFilter, setHerbFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [qualityFilter, setQualityFilter] = useState("");
  const [inquiryMessage, setInquiryMessage] = useState<{ id: number; message: string } | null>(null);

  const { data: listings, isLoading, isError } = useFarmListings({
    herb_id: herbFilter ? Number(herbFilter) : undefined,
    location: locationFilter || undefined,
    quality: qualityFilter || undefined,
  });
  const { data: herbs } = useHerbList({ limit: 100 });
  const inquireMut = useInquireListing();
  const deleteMut = useDeleteListing();

  async function handleInquiry(listingId: number) {
    if (!inquiryMessage || inquiryMessage.id !== listingId) {
      setInquiryMessage({ id: listingId, message: "" });
      return;
    }
    await inquireMut.mutateAsync({ listingId, message: inquiryMessage.message });
    setInquiryMessage(null);
  }

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">🌾 Herb Marketplace</h1>
          <p className="text-forest-200 text-sm mt-1">Buy directly from Nigerian herb farmers — fresh, traceable, verified</p>
        </div>
        <div className="flex gap-3">
          <Link to="/farming/demand" className="btn-outline border-white text-white hover:bg-white/10 text-sm">📊 Market Demand</Link>
          {user?.role === "farmer" && (
            <Link to="/farming/create" className="btn-secondary text-sm">➕ List Herbs</Link>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="label">Filter by Herb</label>
            <select className="select" value={herbFilter} onChange={(e) => setHerbFilter(e.target.value)}>
              <option value="">All herbs</option>
              {herbs?.map((h) => <option key={h.id} value={h.id}>{h.name_english}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Location</label>
            <input className="input" placeholder="e.g. Lagos, Kano, Enugu"
              value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)} />
          </div>
          <div>
            <label className="label">Quality Grade</label>
            <select className="select" value={qualityFilter} onChange={(e) => setQualityFilter(e.target.value)}>
              <option value="">All grades</option>
              <option value="premium">Premium</option>
              <option value="standard">Standard</option>
              <option value="economy">Economy</option>
            </select>
          </div>
        </div>
      </div>

      {isLoading && <div className="flex justify-center py-12"><Spinner /></div>}
      {isError && <PageError message="Failed to load marketplace listings." />}
      {!isLoading && listings?.length === 0 && (
        <Empty icon="🌾" title="No listings found" subtitle="Try adjusting your filters or check back later." />
      )}

      {/* Inquiry modal-style inline form */}
      {inquiryMessage && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
            <h3 className="font-bold text-forest-700 text-lg mb-3">Send Inquiry</h3>
            <textarea
              className="input min-h-24 resize-none w-full mb-4"
              placeholder="Write your message to the farmer — quantity needed, delivery requirements, etc."
              value={inquiryMessage.message}
              onChange={(e) => setInquiryMessage({ ...inquiryMessage, message: e.target.value })}
            />
            {inquireMut.data && (
              <div className="mb-3 p-3 bg-forest-50 border border-forest-200 rounded-lg text-sm text-forest-700">
                ✅ {inquireMut.data.message}
              </div>
            )}
            <div className="flex gap-3">
              <button className="btn-primary flex-1" onClick={() => handleInquiry(inquiryMessage.id)}
                disabled={inquireMut.isPending || !inquiryMessage.message}>
                {inquireMut.isPending ? <Spinner /> : "Send →"}
              </button>
              <button className="btn-outline flex-1" onClick={() => { setInquiryMessage(null); inquireMut.reset?.(); }}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {!isLoading && listings && listings.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {listings.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              canDelete={user?.role === "farmer" || user?.role === "admin"}
              onInquire={(id) => setInquiryMessage({ id, message: "" })}
              onDelete={(id) => deleteMut.mutate(id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
