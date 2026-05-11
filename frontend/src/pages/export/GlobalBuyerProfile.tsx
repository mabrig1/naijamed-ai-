import { useState, useEffect } from "react";
import { useMyBuyerProfile, useCreateOrUpdateBuyerProfile } from "../../hooks/useExport";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner } from "../../components/Layout";
import { Link } from "react-router-dom";

const COUNTRIES = [
  "Germany","United Kingdom","United States","France","Netherlands","Canada",
  "UAE","Saudi Arabia","China","Japan","India","Australia","South Africa",
  "Ghana","Kenya","Belgium","Switzerland","Sweden","Norway","Denmark",
];

const INCOTERMS = ["EXW","FCA","FOB","CFR","CIF","DAP","DDP"];
const CERTS_REQUIRED = ["NAFDAC","NEPC","NAQS","ISO 22000","Organic","Fair Trade","Halal","Kosher","EU Organic"];
const VOLUME_RANGES = ["< 100 kg/mo","100–500 kg/mo","500–1,000 kg/mo","1,000–5,000 kg/mo","> 5,000 kg/mo"];

export default function GlobalBuyerProfile() {
  const { data: profile, isLoading } = useMyBuyerProfile();
  const { data: herbs } = useHerbList({ limit: 100 });
  const saveMut = useCreateOrUpdateBuyerProfile();

  const [form, setForm] = useState({
    company_name: "",
    country: "",
    contact_email: "",
    preferred_herbs: [] as string[],
    monthly_volume_range: "",
    preferred_incoterms: [] as string[],
    certifications_required: [] as string[],
  });

  const [saved, setSaved] = useState(false);

  // Pre-fill from existing profile
  useEffect(() => {
    if (profile) {
      setForm({
        company_name: profile.company_name,
        country: profile.country,
        contact_email: profile.contact_email,
        preferred_herbs: profile.preferred_herbs,
        monthly_volume_range: `${profile.monthly_volume_kg} kg/mo`,
        preferred_incoterms: profile.preferred_incoterms,
        certifications_required: profile.certifications_required,
      });
    }
  }, [profile]);

  function toggleArray(
    key: "preferred_herbs" | "preferred_incoterms" | "certifications_required",
    value: string
  ) {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(value)
        ? f[key].filter((v) => v !== value)
        : [...f[key], value],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const monthlyKg = (() => {
      const map: Record<string, number> = {
        "< 100 kg/mo": 50,
        "100–500 kg/mo": 250,
        "500–1,000 kg/mo": 750,
        "1,000–5,000 kg/mo": 2500,
        "> 5,000 kg/mo": 7500,
      };
      return map[form.monthly_volume_range] ?? 0;
    })();
    await saveMut.mutateAsync({ ...form, monthly_volume_kg: monthlyKg });
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  if (isLoading) return <div className="flex justify-center py-16"><Spinner className="w-8 h-8" /></div>;

  const hasProfile = !!profile;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-6 rounded-2xl">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold">🌍 Global Buyer Profile</h1>
            <p className="text-forest-100 text-sm mt-1">
              Register your import needs and get AI-matched with Nigerian herb exporters
            </p>
          </div>
          {hasProfile && profile.verified && (
            <span className="badge-green text-sm">✓ Verified Buyer</span>
          )}
        </div>
      </div>

      {/* Stats if profile exists */}
      {hasProfile && profile.ai_recommendations?.length > 0 && (
        <div className="card">
          <h2 className="font-bold text-forest-700 mb-4 flex items-center gap-2">
            <span>🤖</span> AI-Recommended Listings for You
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {profile.ai_recommendations.slice(0, 3).map((listing) => (
              <Link
                key={listing.id}
                to={`/export/listings/${listing.id}`}
                className="border border-forest-100 rounded-xl p-4 hover:border-forest-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold text-gray-800 text-sm">{listing.herb_name}</p>
                  <span className="text-xs bg-forest-100 text-forest-700 px-2 py-0.5 rounded-full">
                    Grade {listing.grade}
                  </span>
                </div>
                <p className="text-forest-600 font-bold">${listing.price_per_kg_usd.toFixed(2)}/kg</p>
                <p className="text-xs text-gray-400 mt-1">
                  {listing.quantity_kg.toLocaleString()} kg · {listing.origin_state}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Profile form */}
      <form onSubmit={handleSubmit} className="space-y-5">

        {/* Company & contact */}
        <div className="card space-y-4">
          <h2 className="font-bold text-forest-700 text-lg">🏢 Company Information</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label">Company Name *</label>
              <input className="input" required placeholder="Your company name"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })} />
            </div>
            <div>
              <label className="label">Country *</label>
              <select className="select" required value={form.country}
                onChange={(e) => setForm({ ...form, country: e.target.value })}>
                <option value="">Select country</option>
                {COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="label">Business Email *</label>
              <input className="input" type="email" required placeholder="procurement@company.com"
                value={form.contact_email}
                onChange={(e) => setForm({ ...form, contact_email: e.target.value })} />
            </div>
          </div>
        </div>

        {/* Herb preferences */}
        <div className="card space-y-4">
          <h2 className="font-bold text-forest-700 text-lg">🌿 Herb Preferences</h2>
          <p className="text-sm text-gray-500">Select herbs you regularly import (multi-select)</p>
          <div className="flex flex-wrap gap-2">
            {herbs?.map((h) => (
              <button
                key={h.id}
                type="button"
                onClick={() => toggleArray("preferred_herbs", h.name_english)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  form.preferred_herbs.includes(h.name_english)
                    ? "bg-forest-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                {h.name_english}
              </button>
            ))}
          </div>
          {form.preferred_herbs.length > 0 && (
            <p className="text-xs text-forest-600">
              ✅ {form.preferred_herbs.length} herb{form.preferred_herbs.length > 1 ? "s" : ""} selected
            </p>
          )}
        </div>

        {/* Volume & logistics */}
        <div className="card space-y-4">
          <h2 className="font-bold text-forest-700 text-lg">📦 Volume & Logistics</h2>
          <div>
            <label className="label">Monthly Import Volume</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {VOLUME_RANGES.map((v) => (
                <button key={v} type="button"
                  onClick={() => setForm({ ...form, monthly_volume_range: v })}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    form.monthly_volume_range === v
                      ? "bg-forest-600 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}>
                  {v}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label">Preferred Incoterms</label>
            <div className="flex flex-wrap gap-2 mt-1">
              {INCOTERMS.map((t) => (
                <button key={t} type="button"
                  onClick={() => toggleArray("preferred_incoterms", t)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    form.preferred_incoterms.includes(t)
                      ? "bg-gold-400 text-forest-900"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}>
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Certification requirements */}
        <div className="card space-y-4">
          <h2 className="font-bold text-forest-700 text-lg">📋 Required Certifications</h2>
          <p className="text-sm text-gray-500">Which certifications must your suppliers hold?</p>
          <div className="flex flex-wrap gap-2">
            {CERTS_REQUIRED.map((cert) => (
              <button key={cert} type="button"
                onClick={() => toggleArray("certifications_required", cert)}
                className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                  form.certifications_required.includes(cert)
                    ? "bg-forest-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}>
                {cert}
              </button>
            ))}
          </div>
        </div>

        {/* Submit */}
        {saveMut.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
            ⚠️ Failed to save profile. Please try again.
          </div>
        )}

        {saved && (
          <div className="bg-forest-50 border border-forest-200 rounded-lg p-3 text-sm text-forest-700">
            ✅ Profile saved! AI is matching you with relevant herb exporters.
          </div>
        )}

        <button type="submit" className="btn-primary w-full text-base py-3"
          disabled={saveMut.isPending || !form.company_name || !form.country}>
          {saveMut.isPending ? (
            <><Spinner /> Saving...</>
          ) : hasProfile ? (
            "💾 Update Buyer Profile"
          ) : (
            "🌍 Register as Global Buyer"
          )}
        </button>
      </form>
    </div>
  );
}
