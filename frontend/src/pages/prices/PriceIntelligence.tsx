import { useState } from "react";
import {
  usePriceIndex,
  useHerbPriceHistory,
  usePriceForecast,
  useBestTimeToSell,
  usePriceAlerts,
  useSubscribePriceAlert,
} from "../../hooks/usePrices";
import type { MarketRegion, PriceIndexItem } from "../../hooks/usePrices";
import { useHerbList } from "../../hooks/useHerbs";
import { Spinner, Empty, PageError } from "../../components/Layout";

// ── Price chart (pure SVG, no external lib) ───────────────────────────────────

function PriceLineChart({
  points,
  herbName,
  region,
}: {
  points: Array<{ date: string; price: number; projected: boolean }>;
  herbName: string;
  region: string;
}) {
  if (!points.length) return null;

  const W = 600, H = 180;
  const PAD = { t: 16, r: 24, b: 36, l: 52 };
  const cw = W - PAD.l - PAD.r;
  const ch = H - PAD.t - PAD.b;

  const prices = points.map((p) => p.price);
  const minP = Math.min(...prices) * 0.95;
  const maxP = Math.max(...prices) * 1.05;
  const pRange = maxP - minP || 1;

  const xs = points.map((_, i) => PAD.l + (i / Math.max(points.length - 1, 1)) * cw);
  const ys = points.map((p) => PAD.t + ch - ((p.price - minP) / pRange) * ch);

  // Split at projection boundary
  const splitIdx = points.findIndex((p) => p.projected);
  const histPoints = splitIdx === -1 ? points : points.slice(0, splitIdx + 1);
  const projPoints = splitIdx === -1 ? [] : points.slice(splitIdx);

  function makePath(pts: typeof points, startIdx: number) {
    return pts.map((_, i) => {
      const idx = startIdx + i;
      return `${i === 0 ? "M" : "L"} ${xs[idx].toFixed(1)} ${ys[idx].toFixed(1)}`;
    }).join(" ");
  }

  const histPath = makePath(histPoints, 0);
  const projPath = projPoints.length > 1 ? makePath(projPoints, splitIdx) : "";

  // Y-axis labels
  const yLabels = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    y: PAD.t + ch * (1 - f),
    label: `$${(minP + pRange * f).toFixed(2)}`,
  }));

  // X-axis labels (every ~6 points)
  const xStep = Math.max(1, Math.floor(points.length / 5));
  const xLabels = points
    .filter((_, i) => i % xStep === 0 || i === points.length - 1)
    .map((_p, j) => {
      const i = j * xStep >= points.length ? points.length - 1 : j * xStep;
      const date = new Date(points[i].date);
      return { x: xs[i], label: date.toLocaleDateString("en-US", { month: "short", day: "numeric" }) };
    });

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2">
        {herbName} · <span className="capitalize">{region.replace(/_/g, " ")}</span> market
        {projPoints.length > 0 && (
          <span className="ml-2 text-purple-600">— — 90-day projection</span>
        )}
      </p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full border border-gray-100 rounded-xl bg-white" style={{ height: "180px" }}>
        {/* Grid */}
        {yLabels.map(({ y, label }) => (
          <g key={label}>
            <line x1={PAD.l} y1={y} x2={W - PAD.r} y2={y} stroke="#f3f4f6" strokeWidth="1" />
            <text x={PAD.l - 5} y={y + 4} fontSize="9" fill="#9ca3af" textAnchor="end">{label}</text>
          </g>
        ))}

        {/* Projection shading */}
        {projPoints.length > 0 && (
          <rect
            x={xs[splitIdx]}
            y={PAD.t}
            width={W - PAD.r - xs[splitIdx]}
            height={ch}
            fill="#7c3aed"
            fillOpacity="0.04"
          />
        )}

        {/* Historical line */}
        {histPath && (
          <path d={histPath} fill="none" stroke="#1B4332" strokeWidth="2.5" strokeLinejoin="round" />
        )}

        {/* Projection line */}
        {projPath && (
          <path d={projPath} fill="none" stroke="#7c3aed" strokeWidth="2" strokeDasharray="5,3" strokeLinejoin="round" />
        )}

        {/* Last historical dot */}
        {splitIdx > 0 && (
          <circle cx={xs[splitIdx - 1]} cy={ys[splitIdx - 1]} r="4" fill="#1B4332" />
        )}

        {/* X labels */}
        {xLabels.map(({ x, label }) => (
          <text key={label} x={x} y={H - 6} fontSize="8" fill="#9ca3af" textAnchor="middle">{label}</text>
        ))}
      </svg>
    </div>
  );
}

// ── Trend arrow ───────────────────────────────────────────────────────────────

function TrendBadge({ trend, pct }: { trend: "up" | "down" | "stable"; pct?: number }) {
  if (trend === "up") return (
    <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-emerald-700">
      ▲ {pct !== undefined ? `${Math.abs(pct).toFixed(1)}%` : "Up"}
    </span>
  );
  if (trend === "down") return (
    <span className="inline-flex items-center gap-0.5 text-xs font-semibold text-red-600">
      ▼ {pct !== undefined ? `${Math.abs(pct).toFixed(1)}%` : "Down"}
    </span>
  );
  return <span className="text-xs font-semibold text-gray-400">→ Stable</span>;
}

const REGIONS: MarketRegion[] = ["europe", "north_america", "asia", "middle_east", "africa"];
const REGION_FLAGS: Record<MarketRegion, string> = {
  europe: "🇪🇺", north_america: "🌎", asia: "🌏", middle_east: "🕌", africa: "🌍",
};
const REGION_LABELS: Record<MarketRegion, string> = {
  europe: "Europe", north_america: "North America", asia: "Asia",
  middle_east: "Middle East", africa: "Africa",
};

export default function PriceIntelligence() {
  const [regionFilter, setRegionFilter] = useState<MarketRegion | "">("");
  const [selectedHerbId, setSelectedHerbId] = useState<number | null>(null);
  const [selectedRegion, setSelectedRegion] = useState<MarketRegion>("europe");
  const [sortBy, setSortBy] = useState<"price" | "trend" | "herb">("herb");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [alertForm, setAlertForm] = useState({ threshold: "", when: "above" as "above" | "below" });
  const [alertSaved, setAlertSaved] = useState(false);

  const { data: herbs } = useHerbList({ limit: 100 });
  const { data: priceIndex, isLoading, isError } = usePriceIndex({
    region: regionFilter || undefined,
    limit: 200,
  });
  const { data: history } = useHerbPriceHistory(
    selectedHerbId ?? 0,
    selectedRegion
  );
  const { data: forecast, isFetching: forecastLoading } = usePriceForecast(
    selectedHerbId ?? 0,
    selectedRegion
  );
  const { data: bestTime, isFetching: bestLoading } = useBestTimeToSell(selectedHerbId ?? 0);
  const { data: alerts } = usePriceAlerts();
  const alertMut = useSubscribePriceAlert();

  // Sort price index
  const sortedItems = [...(priceIndex?.items ?? [])].sort((a, b) => {
    let cmp = 0;
    if (sortBy === "price") cmp = a.price_per_kg_usd - b.price_per_kg_usd;
    else if (sortBy === "trend") cmp = a.trend.localeCompare(b.trend);
    else cmp = a.herb_name.localeCompare(b.herb_name);
    return sortDir === "asc" ? cmp : -cmp;
  });

  function toggleSort(col: typeof sortBy) {
    if (sortBy === col) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortBy(col); setSortDir("asc"); }
  }

  const SortIcon = ({ col }: { col: typeof sortBy }) =>
    sortBy === col ? (sortDir === "asc" ? <span> ↑</span> : <span> ↓</span>) : null;

  async function handleAlertSubscribe(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedHerbId || !alertForm.threshold) return;
    await alertMut.mutateAsync({
      herb_id: selectedHerbId,
      threshold_usd: Number(alertForm.threshold),
      alert_when: alertForm.when,
    });
    setAlertSaved(true);
    setTimeout(() => setAlertSaved(false), 3000);
  }

  // Build chart points from history + forecast projection
  const chartPoints = (() => {
    const histPts = history?.prices.map((p) => ({ ...p, price: p.price_per_kg_usd, projected: false })) ?? [];
    if (!forecast) return histPts;
    const lastDate = histPts[histPts.length - 1]?.date;
    if (!lastDate) return histPts;
    const projPts = forecast.projection_points
      .filter((p) => p.projected)
      .map((p) => ({ date: p.date, price: p.price, projected: true }));
    return [...histPts, ...projPts];
  })();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-forest-700 to-forest-500 text-white px-6 py-6 rounded-2xl">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <span>📈</span> Price Intelligence
            </h1>
            <p className="text-forest-100 text-sm mt-1">
              Real-time herb prices across 5 global markets — with AI forecasting
            </p>
            {priceIndex?.as_of && (
              <p className="text-forest-200 text-xs mt-1">
                Last updated: {new Date(priceIndex.as_of).toLocaleString("en-NG", {
                  day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
                })}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <select
              className="bg-white/10 text-white border border-white/20 rounded-lg px-3 py-2 text-sm"
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value as MarketRegion | "")}
            >
              <option value="">All Regions</option>
              {REGIONS.map((r) => (
                <option key={r} value={r}>{REGION_FLAGS[r]} {REGION_LABELS[r]}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Top stats */}
      {priceIndex && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {REGIONS.map((r) => {
            const regionItems = priceIndex.items.filter((i) => i.region === r);
            const avg = regionItems.length
              ? regionItems.reduce((s, i) => s + i.price_per_kg_usd, 0) / regionItems.length
              : null;
            const upCount = regionItems.filter((i) => i.trend === "up").length;
            return (
              <button
                key={r}
                onClick={() => setRegionFilter(regionFilter === r ? "" : r)}
                className={`card py-3 text-center transition-all ${
                  regionFilter === r ? "border-forest-400 bg-forest-50 shadow" : "hover:border-gray-300"
                }`}
              >
                <p className="text-xl">{REGION_FLAGS[r]}</p>
                <p className="text-xs font-semibold text-gray-600 mt-1">{REGION_LABELS[r]}</p>
                {avg !== null && (
                  <p className="text-sm font-bold text-forest-700 mt-0.5">${avg.toFixed(2)}</p>
                )}
                {upCount > 0 && (
                  <p className="text-xs text-emerald-600">▲ {upCount} rising</p>
                )}
              </button>
            );
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Price index table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card overflow-hidden p-0">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-bold text-gray-800">
                📊 Price Index {priceIndex && (
                  <span className="text-xs font-normal text-gray-400 ml-1">
                    ({sortedItems.length} records)
                  </span>
                )}
              </h2>
            </div>
            {isLoading && (
              <div className="flex justify-center py-12"><Spinner /></div>
            )}
            {isError && (
              <div className="p-4"><PageError message="Failed to load price data." /></div>
            )}
            {!isLoading && sortedItems.length === 0 && (
              <div className="p-4"><Empty icon="📊" title="No price data available" /></div>
            )}
            {!isLoading && sortedItems.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                    <tr>
                      <th className="text-left px-5 py-3 cursor-pointer hover:text-gray-700"
                        onClick={() => toggleSort("herb")}>
                        Herb <SortIcon col="herb" />
                      </th>
                      <th className="text-left px-3 py-3">Region</th>
                      <th className="text-right px-3 py-3 cursor-pointer hover:text-gray-700"
                        onClick={() => toggleSort("price")}>
                        Price/kg <SortIcon col="price" />
                      </th>
                      <th className="text-right px-3 py-3 cursor-pointer hover:text-gray-700"
                        onClick={() => toggleSort("trend")}>
                        Trend <SortIcon col="trend" />
                      </th>
                      <th className="text-right px-5 py-3">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {sortedItems.slice(0, 50).map((item: PriceIndexItem, i) => (
                      <tr key={i}
                        className={`hover:bg-forest-50 transition-colors cursor-pointer ${
                          selectedHerbId === item.herb_id ? "bg-forest-50" : ""
                        }`}
                        onClick={() => {
                          setSelectedHerbId(item.herb_id);
                          setSelectedRegion(item.region);
                        }}
                      >
                        <td className="px-5 py-3">
                          <p className="font-medium text-gray-800">{item.herb_name}</p>
                          <p className="text-xs text-gray-400">
                            {new Date(item.recorded_date).toLocaleDateString("en-NG", {
                              day: "numeric", month: "short",
                            })}
                          </p>
                        </td>
                        <td className="px-3 py-3">
                          <span className="text-xs">
                            {REGION_FLAGS[item.region]} {REGION_LABELS[item.region]}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-right font-bold text-forest-700">
                          ${item.price_per_kg_usd.toFixed(2)}
                        </td>
                        <td className="px-3 py-3 text-right">
                          <TrendBadge trend={item.trend} pct={item.change_pct_30d} />
                        </td>
                        <td className="px-5 py-3 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedHerbId(item.herb_id);
                              setSelectedRegion(item.region);
                            }}
                            className="text-xs text-forest-600 hover:text-forest-800 font-medium"
                          >
                            Forecast →
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Forecast chart */}
          {selectedHerbId && (
            <div className="card space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <h2 className="font-bold text-gray-800">📉 Price History & 90-Day Forecast</h2>
                <div className="flex gap-2">
                  {REGIONS.map((r) => (
                    <button key={r}
                      onClick={() => setSelectedRegion(r)}
                      title={REGION_LABELS[r]}
                      className={`w-8 h-8 rounded-full text-sm transition-colors ${
                        selectedRegion === r
                          ? "bg-forest-600 text-white"
                          : "bg-gray-100 hover:bg-gray-200"
                      }`}>
                      {REGION_FLAGS[r]}
                    </button>
                  ))}
                </div>
              </div>

              {forecastLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : chartPoints.length > 0 ? (
                <PriceLineChart
                  points={chartPoints}
                  herbName={herbs?.find((h) => h.id === selectedHerbId)?.name_english ?? ""}
                  region={selectedRegion}
                />
              ) : (
                <p className="text-sm text-gray-400 text-center py-6">No price history available for this herb/region combination.</p>
              )}

              {forecast && (
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "30-day forecast", value: `$${forecast.forecast_30d.toFixed(2)}` },
                    { label: "90-day forecast", value: `$${forecast.forecast_90d.toFixed(2)}` },
                    { label: "Confidence", value: forecast.confidence.toUpperCase() },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-gray-50 rounded-lg p-3 text-center">
                      <p className="text-xs text-gray-400 mb-0.5">{label}</p>
                      <p className="font-bold text-gray-800">{value}</p>
                    </div>
                  ))}
                </div>
              )}

              {forecast?.recommendation && (
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-4 text-sm text-purple-800">
                  <p className="font-semibold mb-1">🤖 AI Recommendation</p>
                  <p>{forecast.recommendation}</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-4">

          {/* Best time to sell */}
          <div className="card">
            <h2 className="font-bold text-forest-700 mb-3 flex items-center gap-2">
              <span>⏰</span> Best Time to Sell
            </h2>
            {!selectedHerbId ? (
              <p className="text-sm text-gray-400">Select a herb from the price table to see AI recommendation.</p>
            ) : bestLoading ? (
              <div className="flex justify-center py-4"><Spinner /></div>
            ) : bestTime ? (
              <div className="space-y-3">
                <div className="bg-forest-50 rounded-xl p-3 border border-forest-100">
                  <p className="text-xs text-gray-500 mb-0.5">Best Market</p>
                  <p className="font-bold text-forest-700 text-lg">
                    {REGION_FLAGS[bestTime.best_market]} {REGION_LABELS[bestTime.best_market]}
                  </p>
                  <p className="text-xs font-medium text-forest-600 mt-0.5">
                    Net return: ${bestTime.net_return_per_kg_usd.toFixed(2)}/kg
                  </p>
                </div>
                <div className="text-sm text-gray-600 space-y-1">
                  <p>⏳ Optimal window: {bestTime.best_window_days} days</p>
                  <p>🥈 Second best: {REGION_FLAGS[bestTime.second_best]} {REGION_LABELS[bestTime.second_best]}</p>
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{bestTime.reasoning}</p>
                {bestTime.markets_to_avoid.length > 0 && (
                  <div>
                    <p className="text-xs text-red-600 font-medium">Markets to avoid:</p>
                    <p className="text-xs text-red-500">
                      {bestTime.markets_to_avoid.map((m) => `${REGION_FLAGS[m]} ${REGION_LABELS[m]}`).join(", ")}
                    </p>
                  </div>
                )}
              </div>
            ) : null}
          </div>

          {/* Alert subscription */}
          <div className="card">
            <h2 className="font-bold text-forest-700 mb-3 flex items-center gap-2">
              <span>🔔</span> Price Alerts
            </h2>
            {!selectedHerbId ? (
              <p className="text-sm text-gray-400">Select a herb to set a price alert.</p>
            ) : (
              <form onSubmit={handleAlertSubscribe} className="space-y-3">
                <div>
                  <label className="label">Alert when price is</label>
                  <select className="select text-sm" value={alertForm.when}
                    onChange={(e) => setAlertForm({ ...alertForm, when: e.target.value as "above" | "below" })}>
                    <option value="above">Above threshold</option>
                    <option value="below">Below threshold</option>
                  </select>
                </div>
                <div>
                  <label className="label">Threshold (USD/kg)</label>
                  <input className="input text-sm" type="number" step="0.01" min="0.01"
                    placeholder="e.g. 15.00"
                    value={alertForm.threshold}
                    onChange={(e) => setAlertForm({ ...alertForm, threshold: e.target.value })} />
                </div>
                {alertSaved && (
                  <p className="text-xs text-forest-600">✅ Alert saved!</p>
                )}
                <button type="submit" className="btn-primary w-full text-sm"
                  disabled={alertMut.isPending || !alertForm.threshold}>
                  {alertMut.isPending ? <Spinner /> : "🔔 Set Alert"}
                </button>
              </form>
            )}

            {/* Existing alerts */}
            {alerts && alerts.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-xs font-medium text-gray-500 mb-2">Active alerts</p>
                <div className="space-y-1.5">
                  {alerts.map((a) => (
                    <div key={a.id} className="flex items-center justify-between text-xs">
                      <span className="text-gray-700">{a.herb_name}</span>
                      <span className={a.alert_when === "above" ? "text-emerald-600" : "text-red-500"}>
                        {a.alert_when === "above" ? "▲" : "▼"} ${a.threshold_usd.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Submit price */}
          <div className="card bg-forest-50 border-forest-200">
            <h3 className="font-bold text-forest-700 mb-2 text-sm">📤 Submit Market Price</h3>
            <p className="text-xs text-gray-500 mb-3">
              Help keep the price index accurate by submitting a price you observed.
            </p>
            <a href="/prices/submit" className="btn-outline text-sm w-full text-center block">
              Submit Price Data →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
