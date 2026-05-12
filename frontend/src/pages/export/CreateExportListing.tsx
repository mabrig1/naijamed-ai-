import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useCreateExportListing, useHSCodeLookup } from "../../hooks/useExport";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner } from "../../components/Layout";

const NIGERIAN_STATES = [
  "Abia","Adamawa","Akwa Ibom","Anambra","Bauchi","Bayelsa","Benue","Borno",
  "Cross River","Delta","Ebonyi","Edo","Ekiti","Enugu","FCT","Gombe","Imo",
  "Jigawa","Kaduna","Kano","Katsina","Kebbi","Kogi","Kwara","Lagos","Nasarawa",
  "Niger","Ogun","Ondo","Osun","Oyo","Plateau","Rivers","Sokoto","Taraba","Yobe","Zamfara",
];

const DESTINATION_COUNTRIES = [
  "Germany","United Kingdom","United States","France","Netherlands","Canada","UAE",
  "Saudi Arabia","China","Japan","India","Australia","South Africa","Ghana","Kenya",
];

const INCOTERMS = ["EXW","FCA","FOB","CFR","CIF","DAP","DDP","FAS","CPT","CIP"];

interface FormState {
  herb_id: string;
  grade: "A" | "B" | "C" | "organic";
  quantity_kg: string;
  price_per_kg_usd: string;
  origin_state: string;
  destination_countries: string[];
  freight_channels: string[];
  incoterms: string[];
  hs_code: string;
  is_organic: boolean;
  description: string;
  gps_lat: string;
  gps_lng: string;
  nafdac_cert: File | null;
  nepc_cert: File | null;
  naqs_cert: File | null;
  images: File[];
}

function FileUploadBox({
  label,
  badge,
  badgeColor,
  file,
  onFile,
  required,
}: {
  label: string;
  badge: string;
  badgeColor: string;
  file: File | null;
  onFile: (f: File | null) => void;
  required?: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);
  return (
    <div
      onClick={() => ref.current?.click()}
      className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
        file ? "border-forest-400 bg-forest-50" : "border-gray-300 hover:border-forest-400"
      }`}
    >
      <input
        ref={ref}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      <div className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold ${badgeColor} mb-2`}>
        {badge}
      </div>
      <p className="text-xs font-medium text-gray-700">{label}</p>
      {file ? (
        <p className="text-xs text-forest-600 mt-1 truncate max-w-[160px] mx-auto">✅ {file.name}</p>
      ) : (
        <p className="text-xs text-gray-400 mt-1">Click to upload PDF or image{required ? " *" : ""}</p>
      )}
    </div>
  );
}

export default function CreateExportListing() {
  const navigate = useNavigate();
  const { data: herbs } = useHerbList({ limit: 100 });
  const createMut = useCreateExportListing();
  const hsLookup = useHSCodeLookup();

  const [form, setForm] = useState<FormState>({
    herb_id: "",
    grade: "A",
    quantity_kg: "",
    price_per_kg_usd: "",
    origin_state: "",
    destination_countries: [],
    freight_channels: [],
    incoterms: [],
    hs_code: "",
    is_organic: false,
    description: "",
    gps_lat: "",
    gps_lng: "",
    nafdac_cert: null,
    nepc_cert: null,
    naqs_cert: null,
    images: [],
  });

  const [step, setStep] = useState(1);
  const [gpsLoading, setGpsLoading] = useState(false);

  const selectedHerb = herbs?.find((h) => h.id === Number(form.herb_id));

  // Auto-fill HS code when herb changes
  async function handleHerbChange(herbId: string) {
    setForm((f) => ({ ...f, herb_id: herbId, hs_code: "" }));
    const herb = herbs?.find((h) => h.id === Number(herbId));
    if (!herb) return;
    try {
      const result = await hsLookup.mutateAsync(herb.name_english);
      setForm((f) => ({ ...f, hs_code: result.hs_code }));
    } catch {
      // non-fatal — user can type manually
    }
  }

  function toggleArray(
    key: "destination_countries" | "freight_channels" | "incoterms",
    value: string
  ) {
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(value)
        ? f[key].filter((v) => v !== value)
        : [...f[key], value],
    }));
  }

  function detectGPS() {
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setForm((f) => ({
          ...f,
          gps_lat: pos.coords.latitude.toFixed(6),
          gps_lng: pos.coords.longitude.toFixed(6),
        }));
        setGpsLoading(false);
      },
      () => setGpsLoading(false)
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const fd = new FormData();
    Object.entries(form).forEach(([k, v]) => {
      if (v === null || v === undefined) return;
      if (k === "destination_countries" || k === "freight_channels" || k === "incoterms") {
        (v as string[]).forEach((item) => fd.append(k, item));
      } else if (k === "images") {
        (v as File[]).forEach((f) => fd.append("images", f));
      } else if (k === "nafdac_cert" || k === "nepc_cert" || k === "naqs_cert") {
        if (v) fd.append(k, v as File);
      } else {
        fd.append(k, String(v));
      }
    });
    const listing = await createMut.mutateAsync(fd);
    navigate(`/export/listings/${listing.id}`);
  }

  const steps = [
    { n: 1, label: "Herb & Pricing" },
    { n: 2, label: "Location & Logistics" },
    { n: 3, label: "Certifications" },
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-forest-600 text-white px-6 py-5 rounded-xl">
        <h1 className="text-2xl font-bold">➕ Create Export Listing</h1>
        <p className="text-forest-200 text-sm mt-1">List your NAFDAC-certified herbs for global buyers</p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2">
        {steps.map((s) => (
          <button
            key={s.n}
            onClick={() => setStep(s.n)}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              step === s.n
                ? "bg-forest-600 text-white"
                : step > s.n
                ? "bg-forest-100 text-forest-700"
                : "bg-gray-100 text-gray-400"
            }`}
          >
            {step > s.n ? "✓ " : `${s.n}. `}{s.label}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">

        {/* Step 1: Herb & Pricing */}
        {step === 1 && (
          <div className="card space-y-4">
            <h2 className="font-bold text-forest-700 text-lg">🌿 Herb Details & Pricing</h2>

            <div>
              <label className="label">Herb Type *</label>
              <select className="select" required value={form.herb_id}
                onChange={(e) => handleHerbChange(e.target.value)}>
                <option value="">Select a herb</option>
                {herbs?.map((h) => <option key={h.id} value={h.id}>{h.name_english}</option>)}
              </select>
              {selectedHerb?.scientific_name && (
                <p className="text-xs text-gray-400 mt-1 italic">{selectedHerb.scientific_name}</p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Grade *</label>
                <select className="select" required value={form.grade}
                  onChange={(e) => setForm({ ...form, grade: e.target.value as FormState["grade"] })}>
                  <option value="A">Grade A — Export Premium</option>
                  <option value="B">Grade B — Standard</option>
                  <option value="C">Grade C — Economy</option>
                  <option value="organic">🌿 Certified Organic</option>
                </select>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" className="w-4 h-4 rounded accent-forest-600"
                    checked={form.is_organic}
                    onChange={(e) => setForm({ ...form, is_organic: e.target.checked })} />
                  <span className="text-sm font-medium text-gray-700">🌿 Organic Certified</span>
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Quantity Available (kg) *</label>
                <input className="input" type="number" min="1" required placeholder="e.g. 500"
                  value={form.quantity_kg}
                  onChange={(e) => setForm({ ...form, quantity_kg: e.target.value })} />
              </div>
              <div>
                <label className="label">Price per kg (USD) *</label>
                <input className="input" type="number" step="0.01" min="0.01" required placeholder="e.g. 12.50"
                  value={form.price_per_kg_usd}
                  onChange={(e) => setForm({ ...form, price_per_kg_usd: e.target.value })} />
              </div>
            </div>

            {/* AI HS Code */}
            <div>
              <label className="label flex items-center gap-2">
                HS Code
                {hsLookup.isPending && <Spinner />}
                {form.hs_code && <span className="badge-green ml-1">🤖 AI-filled</span>}
              </label>
              <input className="input" type="text" placeholder="Auto-filled when herb is selected"
                value={form.hs_code}
                onChange={(e) => setForm({ ...form, hs_code: e.target.value })} />
              {hsLookup.isError && (
                <p className="text-xs text-amber-600 mt-1">⚠️ Could not auto-detect HS code — enter manually</p>
              )}
            </div>

            <div>
              <label className="label">Description</label>
              <textarea className="input min-h-24 resize-none"
                placeholder="Describe your herb: processing method, moisture content, packaging details, minimum order..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>

            <div>
              <label className="label">Target Markets</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {DESTINATION_COUNTRIES.map((c) => (
                  <button key={c} type="button"
                    onClick={() => toggleArray("destination_countries", c)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      form.destination_countries.includes(c)
                        ? "bg-forest-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}>
                    {c}
                  </button>
                ))}
              </div>
            </div>

            <button type="button" onClick={() => setStep(2)} className="btn-primary w-full"
              disabled={!form.herb_id || !form.quantity_kg || !form.price_per_kg_usd}>
              Next: Location & Logistics →
            </button>
          </div>
        )}

        {/* Step 2: Location & Logistics */}
        {step === 2 && (
          <div className="card space-y-4">
            <h2 className="font-bold text-forest-700 text-lg">📍 Farm Location & Logistics</h2>

            <div>
              <label className="label">Origin State *</label>
              <select className="select" required value={form.origin_state}
                onChange={(e) => setForm({ ...form, origin_state: e.target.value })}>
                <option value="">Select state</option>
                {NIGERIAN_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>

            {/* GPS picker */}
            <div>
              <label className="label">Farm GPS Coordinates</label>
              <div className="grid grid-cols-2 gap-3">
                <input className="input" type="number" step="0.000001" placeholder="Latitude"
                  value={form.gps_lat}
                  onChange={(e) => setForm({ ...form, gps_lat: e.target.value })} />
                <input className="input" type="number" step="0.000001" placeholder="Longitude"
                  value={form.gps_lng}
                  onChange={(e) => setForm({ ...form, gps_lng: e.target.value })} />
              </div>
              <button type="button" onClick={detectGPS} disabled={gpsLoading}
                className="mt-2 text-xs text-forest-600 hover:text-forest-800 flex items-center gap-1 font-medium">
                {gpsLoading ? <Spinner /> : "📡"} Use my current location
              </button>
              {form.gps_lat && form.gps_lng && (
                <p className="text-xs text-forest-600 mt-1">
                  ✅ GPS set: {form.gps_lat}, {form.gps_lng}
                </p>
              )}
            </div>

            {/* Freight channels */}
            <div>
              <label className="label">Freight Channels Available</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {[
                  { key: "air", label: "✈️ Air Freight" },
                  { key: "sea", label: "🚢 Sea Freight" },
                  { key: "road", label: "🚛 Road Freight" },
                  { key: "ecommerce", label: "📦 E-Commerce" },
                ].map(({ key, label }) => (
                  <button key={key} type="button"
                    onClick={() => toggleArray("freight_channels", key)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      form.freight_channels.includes(key)
                        ? "bg-forest-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Incoterms */}
            <div>
              <label className="label">Accepted Incoterms</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {INCOTERMS.map((t) => (
                  <button key={t} type="button"
                    onClick={() => toggleArray("incoterms", t)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      form.incoterms.includes(t)
                        ? "bg-gold-400 text-forest-900"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}>
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(1)} className="btn-outline flex-1">← Back</button>
              <button type="button" onClick={() => setStep(3)} className="btn-primary flex-1"
                disabled={!form.origin_state}>
                Next: Certifications →
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Certifications & Submit */}
        {step === 3 && (
          <div className="card space-y-4">
            <h2 className="font-bold text-forest-700 text-lg">📋 Certifications & Documents</h2>
            <p className="text-sm text-gray-500">Upload your regulatory certificates. NAFDAC is required for all export listings.</p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <FileUploadBox
                label="NAFDAC Certificate"
                badge="NAFDAC"
                badgeColor="bg-forest-600 text-white"
                file={form.nafdac_cert}
                onFile={(f) => setForm({ ...form, nafdac_cert: f })}
                required
              />
              <FileUploadBox
                label="NEPC Registration"
                badge="NEPC"
                badgeColor="bg-gold-400 text-forest-900"
                file={form.nepc_cert}
                onFile={(f) => setForm({ ...form, nepc_cert: f })}
              />
              <FileUploadBox
                label="NAQS Certificate"
                badge="NAQS"
                badgeColor="bg-forest-800 text-white"
                file={form.naqs_cert}
                onFile={(f) => setForm({ ...form, naqs_cert: f })}
              />
            </div>

            {/* Product images */}
            <div>
              <label className="label">Product Images</label>
              <div
                onClick={() => document.getElementById("img-upload")?.click()}
                className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:border-forest-400 transition-colors"
              >
                <input id="img-upload" type="file" accept="image/*" multiple className="hidden"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? []);
                    setForm((f) => ({ ...f, images: [...f.images, ...files].slice(0, 6) }));
                  }} />
                <p className="text-2xl mb-2">🖼️</p>
                <p className="text-sm text-gray-600">Click to upload herb photos (max 6)</p>
                <p className="text-xs text-gray-400">JPG, PNG up to 5MB each</p>
              </div>
              {form.images.length > 0 && (
                <div className="flex gap-2 mt-2 flex-wrap">
                  {form.images.map((_img, i) => (
                    <div key={i} className="relative">
                      <div className="w-14 h-14 bg-forest-50 rounded-lg flex items-center justify-center text-xs text-gray-500 overflow-hidden">
                        🖼️
                      </div>
                      <button type="button"
                        onClick={() => setForm((f) => ({ ...f, images: f.images.filter((_, j) => j !== i) }))}
                        className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full text-xs flex items-center justify-center">
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Summary card */}
            {selectedHerb && (
              <div className="bg-forest-50 rounded-xl p-4 border border-forest-100 text-sm space-y-1.5">
                <p className="font-semibold text-forest-700 mb-2">📋 Listing Summary</p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600">
                  <span>Herb:</span><span className="font-medium">{selectedHerb.name_english}</span>
                  <span>Grade:</span><span className="font-medium">{form.grade}</span>
                  <span>Quantity:</span><span className="font-medium">{form.quantity_kg} kg</span>
                  <span>Price:</span><span className="font-medium">${form.price_per_kg_usd}/kg</span>
                  <span>State:</span><span className="font-medium">{form.origin_state}</span>
                  <span>HS Code:</span><span className="font-medium">{form.hs_code || "Not set"}</span>
                </div>
              </div>
            )}

            {createMut.isError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
                ⚠️ Failed to create listing. Please check all required fields and try again.
              </div>
            )}

            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(2)} className="btn-outline flex-1">← Back</button>
              <button type="submit" className="btn-primary flex-1"
                disabled={createMut.isPending || !form.nafdac_cert}>
                {createMut.isPending ? <><Spinner /> Publishing...</> : "🚀 Publish Listing"}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
