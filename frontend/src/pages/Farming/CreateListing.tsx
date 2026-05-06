import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useHerbList } from "../../hooks/useHerbs";
import { useCreateListing } from "../../hooks/useFarming";
import { Spinner, PageError } from "../../components/Layout";

const QUALITY_OPTIONS = [
  { value: "premium", label: "Premium", desc: "Lab-certified, highest purity", icon: "⭐" },
  { value: "standard", label: "Standard", desc: "Good quality, market-ready", icon: "✅" },
  { value: "economy", label: "Economy", desc: "Bulk supply, lower price point", icon: "📦" },
];

export default function CreateListing() {
  const navigate = useNavigate();
  const { data: herbs } = useHerbList({ limit: 100 });
  const createMut = useCreateListing();

  const [herbId, setHerbId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [location, setLocation] = useState("");
  const [quality, setQuality] = useState<"premium" | "standard" | "economy">("standard");
  const [harvestDate, setHarvestDate] = useState("");
  const [description, setDescription] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await createMut.mutateAsync({
      herb_id: Number(herbId),
      quantity_kg: Number(quantity),
      price_per_kg: Number(price),
      location,
      quality_grade: quality,
      harvest_date: harvestDate || undefined,
      description: description || undefined,
    });
    navigate("/farming");
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">🌿 List Your Herbs</h1>
        <p className="text-forest-200 text-sm mt-1">
          Connect your harvest to pharmaceutical buyers, researchers, and the NaijaMed network.
        </p>
      </div>

      <div className="card">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Herb */}
          <div>
            <label className="label">Herb <span className="text-red-500">*</span></label>
            <select className="select" value={herbId} onChange={(e) => setHerbId(e.target.value)} required>
              <option value="">— Select a herb —</option>
              {herbs?.map((h) => (
                <option key={h.id} value={h.id}>
                  {h.name_english}{h.scientific_name ? ` (${h.scientific_name})` : ""}
                </option>
              ))}
            </select>
          </div>

          {/* Quality */}
          <div>
            <label className="label">Quality Grade <span className="text-red-500">*</span></label>
            <div className="grid grid-cols-3 gap-3">
              {QUALITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setQuality(opt.value as typeof quality)}
                  className={`flex flex-col items-center gap-1.5 p-4 rounded-xl border-2 transition-all text-center ${
                    quality === opt.value
                      ? "border-forest-600 bg-forest-50 text-forest-700"
                      : "border-gray-200 hover:border-forest-300 text-gray-500"
                  }`}
                >
                  <span className="text-2xl">{opt.icon}</span>
                  <span className="text-sm font-semibold">{opt.label}</span>
                  <span className="text-xs text-gray-400">{opt.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Quantity and Price */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Quantity (kg) <span className="text-red-500">*</span></label>
              <input
                type="number" min="0.1" step="0.1" className="input"
                placeholder="e.g. 50"
                value={quantity} onChange={(e) => setQuantity(e.target.value)} required
              />
            </div>
            <div>
              <label className="label">Price per kg (₦) <span className="text-red-500">*</span></label>
              <input
                type="number" min="1" step="1" className="input"
                placeholder="e.g. 2500"
                value={price} onChange={(e) => setPrice(e.target.value)} required
              />
            </div>
          </div>

          {/* Location */}
          <div>
            <label className="label">Location <span className="text-red-500">*</span></label>
            <input className="input" placeholder="e.g. Ogun State, Abeokuta"
              value={location} onChange={(e) => setLocation(e.target.value)} required />
          </div>

          {/* Harvest date */}
          <div>
            <label className="label">Harvest Date <span className="text-gray-400">(optional)</span></label>
            <input type="date" className="input"
              value={harvestDate} onChange={(e) => setHarvestDate(e.target.value)}
              max={new Date().toISOString().split("T")[0]}
            />
          </div>

          {/* Description */}
          <div>
            <label className="label">Additional Notes <span className="text-gray-400">(optional)</span></label>
            <textarea className="input min-h-24 resize-none" rows={3}
              placeholder="Drying method, certifications, packaging details, minimum order quantity…"
              value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>

          {/* Price preview */}
          {quantity && price && (
            <div className="bg-forest-50 border border-forest-200 rounded-lg p-4">
              <p className="text-sm text-forest-700">
                <span className="font-semibold">Total value:</span>{" "}
                ₦{(Number(quantity) * Number(price)).toLocaleString()}
                <span className="text-forest-500 ml-1">({quantity} kg × ₦{Number(price).toLocaleString()})</span>
              </p>
            </div>
          )}

          {createMut.isError && (
            <PageError message="Failed to create listing. Please check your inputs and try again." />
          )}

          <button
            type="submit"
            className="btn-primary w-full py-3 flex items-center justify-center gap-2"
            disabled={createMut.isPending || !herbId || !quantity || !price || !location}
          >
            {createMut.isPending ? <><Spinner /> Publishing…</> : "🌾 Publish Listing →"}
          </button>
        </form>
      </div>
    </div>
  );
}
