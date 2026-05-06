import { useState } from "react";
import { useCalculateFreight } from "../../hooks/useLogistics";
import type { FreightOption } from "../../hooks/useLogistics";
import { Spinner } from "../../components/Layout";

const NIGERIAN_STATES = [
  "Abia","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno",
  "Cross River","Delta","Ebonyi","Edo","Ekiti","Enugu","FCT","Gombe","Imo",
  "Jigawa","Kaduna","Kano","Katsina","Kebbi","Kogi","Kwara","Lagos","Nasarawa",
  "Niger","Ogun","Ondo","Osun","Oyo","Plateau","Rivers","Sokoto","Taraba","Yobe","Zamfara",
];

const DESTINATION_COUNTRIES = [
  "Germany","United Kingdom","United States","France","Netherlands","Canada",
  "UAE","Saudi Arabia","China","Japan","India","Australia","South Africa","Ghana","Kenya",
  "Belgium","Switzerland","Sweden","Norway","Italy","Spain","Poland","Brazil",
];

const HERB_TYPES = [
  "Moringa Powder","Bitter Leaf (Dried)","Turmeric Root","Neem (Dogoyaro)","African Basil",
  "Ginger Root","Garlic","African Pepper","Hibiscus (Zobo)","Aloe Vera",
  "Tiger Nut","Baobab Powder","Black Seed","Shea Butter","Soursop Leaf",
];

function FreightOptionCard({
  channel,
  option,
  recommended,
  onBook,
}: {
  channel: string;
  option: FreightOption;
  recommended: boolean;
  onBook: () => void;
}) {
  const icons: Record<string, string> = {
    air: "✈️", sea: "🚢", road: "🚛", ecommerce: "📦",
  };
  const labels: Record<string, string> = {
    air: "Air Freight", sea: "Sea Freight", road: "Road Freight", ecommerce: "E-Commerce",
  };

  return (
    <div className={`rounded-2xl border-2 p-5 flex flex-col transition-all relative ${
      recommended
        ? "border-forest-500 bg-gradient-to-b from-forest-50 to-white shadow-lg"
        : "border-gray-200 bg-white hover:border-gray-300"
    }`}>
      {recommended && (
        <div className="absolute -top-4 inset-x-0 flex justify-center">
          <span className="bg-forest-600 text-white text-xs font-bold px-4 py-1 rounded-full shadow">
            🤖 Best Option
          </span>
        </div>
      )}
      <div className="text-center mb-4 mt-2">
        <div className="text-3xl mb-1">{icons[channel]}</div>
        <h3 className="font-bold text-gray-800">{labels[channel]}</h3>
      </div>

      {/* Total price */}
      <div className={`text-center py-3 rounded-xl mb-4 ${
        recommended ? "bg-forest-600 text-white" : "bg-gray-100 text-gray-800"
      }`}>
        <p className="text-3xl font-bold">${option.total_usd.toLocaleString()}</p>
        <p className={`text-xs mt-0.5 ${recommended ? "text-forest-100" : "text-gray-500"}`}>
          Total USD
        </p>
      </div>

      {/* Breakdown */}
      <div className="space-y-2 text-sm flex-1">
        {[
          { label: "Freight", value: option.freight_usd },
          { label: "Insurance", value: option.insurance_usd },
          { label: "Handling", value: option.handling_usd },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between text-gray-600">
            <span>{label}</span>
            <span className="font-medium">${value.toLocaleString()}</span>
          </div>
        ))}
        <div className="flex justify-between font-semibold text-gray-800 border-t border-gray-100 pt-2">
          <span>Transit Time</span>
          <span>{option.transit_days} days</span>
        </div>
      </div>

      {option.notes && (
        <p className="text-xs text-gray-400 mt-3 italic leading-relaxed">{option.notes}</p>
      )}

      <button
        onClick={onBook}
        className={`mt-4 w-full py-2.5 rounded-lg text-sm font-semibold transition-colors ${
          recommended
            ? "bg-forest-600 text-white hover:bg-forest-700"
            : "border-2 border-forest-600 text-forest-600 hover:bg-forest-50"
        }`}
      >
        Book This Freight →
      </button>
    </div>
  );
}

export default function FreightQuoteCalculator() {
  const [form, setForm] = useState({
    herb_type: "",
    origin_state: "",
    destination_country: "",
    quantity_kg: "",
  });
  const [booked, setBooked] = useState<string | null>(null);
  const calcMut = useCalculateFreight();
  const quote = calcMut.data;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    calcMut.mutate({
      herb_type: form.herb_type,
      origin_state: form.origin_state,
      destination_country: form.destination_country,
      quantity_kg: Number(form.quantity_kg),
    });
  }

  const channels = ["air", "sea", "road", "ecommerce"] as const;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-6 rounded-2xl">
        <div className="flex items-start gap-3">
          <span className="text-3xl">🚢</span>
          <div>
            <h1 className="text-2xl font-bold">Freight Quote Calculator</h1>
            <p className="text-forest-100 text-sm mt-1">
              Instant quotes for air, sea, road and e-commerce freight from any Nigerian state to the world
            </p>
          </div>
        </div>
      </div>

      {/* Calculator form */}
      <div className="card">
        <h2 className="font-bold text-gray-800 mb-4">📋 Shipment Details</h2>
        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="label">Herb Type *</label>
              <select className="select" required value={form.herb_type}
                onChange={(e) => setForm({ ...form, herb_type: e.target.value })}>
                <option value="">Select herb</option>
                {HERB_TYPES.map((h) => <option key={h} value={h}>{h}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Origin State *</label>
              <select className="select" required value={form.origin_state}
                onChange={(e) => setForm({ ...form, origin_state: e.target.value })}>
                <option value="">Select state</option>
                {NIGERIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Destination Country *</label>
              <select className="select" required value={form.destination_country}
                onChange={(e) => setForm({ ...form, destination_country: e.target.value })}>
                <option value="">Select country</option>
                {DESTINATION_COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Quantity (kg) *</label>
              <input className="input" type="number" min="1" required placeholder="e.g. 500"
                value={form.quantity_kg}
                onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })} />
            </div>
          </div>
          <button type="submit" className="btn-primary w-full sm:w-auto px-8"
            disabled={calcMut.isPending}>
            {calcMut.isPending ? (
              <span className="flex items-center gap-2"><Spinner /> Calculating...</span>
            ) : (
              "🔍 Calculate Freight Quotes"
            )}
          </button>
        </form>
      </div>

      {/* Loading state */}
      {calcMut.isPending && (
        <div className="flex flex-col items-center gap-3 py-12 text-gray-500">
          <Spinner className="w-8 h-8" />
          <p className="text-sm">Calculating quotes from 4 freight channels...</p>
        </div>
      )}

      {/* Results */}
      {quote && !calcMut.isPending && (
        <div className="space-y-4">
          {/* Summary bar */}
          <div className="bg-forest-50 border border-forest-200 rounded-xl px-5 py-4 flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-forest-700">
              <span className="font-semibold">{quote.quantity_kg.toLocaleString()} kg</span> of{" "}
              <span className="font-semibold">{quote.herb_type}</span> from{" "}
              <span className="font-semibold">{quote.origin_state}</span> to{" "}
              <span className="font-semibold">{quote.destination_country}</span>
            </div>
            {quote.ai_recommendation && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-forest-600">🤖 AI recommends:</span>
                <span className="font-bold text-forest-700 capitalize">{quote.ai_recommendation}</span>
              </div>
            )}
          </div>

          {quote.ai_reasoning && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
              <p className="font-semibold mb-1">🤖 AI Analysis</p>
              <p className="leading-relaxed">{quote.ai_reasoning}</p>
            </div>
          )}

          {/* 4 channel cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 pt-2">
            {channels.map((ch) => {
              const opt = quote[ch] as FreightOption | null;
              if (!opt) {
                return (
                  <div key={ch} className="rounded-2xl border-2 border-dashed border-gray-200 p-5 flex flex-col items-center justify-center text-gray-400 min-h-[260px]">
                    <p className="text-2xl mb-2">
                      {ch === "air" ? "✈️" : ch === "sea" ? "🚢" : ch === "road" ? "🚛" : "📦"}
                    </p>
                    <p className="text-sm font-medium capitalize">{ch}</p>
                    <p className="text-xs mt-1">Not available</p>
                  </div>
                );
              }
              return (
                <FreightOptionCard
                  key={ch}
                  channel={ch}
                  option={opt}
                  recommended={quote.ai_recommendation === ch}
                  onBook={() => setBooked(ch)}
                />
              );
            })}
          </div>

          {/* Info cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-4">
            <div className="card py-4">
              <p className="text-xs text-gray-400 mb-1">Price per kg (avg)</p>
              <p className="font-bold text-gray-800 text-lg">
                ${(Math.min(...channels.map((ch) => (quote[ch] as FreightOption | null)?.total_usd ?? Infinity)) / quote.quantity_kg).toFixed(2)}
              </p>
              <p className="text-xs text-gray-400">best channel</p>
            </div>
            <div className="card py-4">
              <p className="text-xs text-gray-400 mb-1">Fastest option</p>
              <p className="font-bold text-gray-800 text-lg capitalize">
                {channels.reduce((best, ch) => {
                  const opt = quote[ch] as FreightOption | null;
                  const bestOpt = quote[best] as FreightOption | null;
                  if (!opt) return best;
                  if (!bestOpt) return ch;
                  return opt.transit_days < bestOpt.transit_days ? ch : best;
                }, channels[0])}
              </p>
              <p className="text-xs text-gray-400">freight</p>
            </div>
            <div className="card py-4">
              <p className="text-xs text-gray-400 mb-1">Most economical</p>
              <p className="font-bold text-gray-800 text-lg capitalize">
                {channels.reduce((best, ch) => {
                  const opt = quote[ch] as FreightOption | null;
                  const bestOpt = quote[best] as FreightOption | null;
                  if (!opt) return best;
                  if (!bestOpt) return ch;
                  return opt.total_usd < bestOpt.total_usd ? ch : best;
                }, channels[0])}
              </p>
              <p className="text-xs text-gray-400">freight</p>
            </div>
          </div>
        </div>
      )}

      {/* Booking confirmation */}
      {booked && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl text-center space-y-4">
            <div className="text-5xl">
              {booked === "air" ? "✈️" : booked === "sea" ? "🚢" : booked === "road" ? "🚛" : "📦"}
            </div>
            <h3 className="font-bold text-xl text-forest-700 capitalize">
              Book {booked} Freight
            </h3>
            <p className="text-gray-500 text-sm">
              To proceed with booking, please create an export order first. Freight booking is linked to a confirmed trade order.
            </p>
            <div className="flex gap-3">
              <a href="/export" className="btn-primary flex-1">Go to Marketplace →</a>
              <button onClick={() => setBooked(null)} className="btn-outline flex-1">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
