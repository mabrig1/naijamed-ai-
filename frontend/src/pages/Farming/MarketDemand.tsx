import { useState } from "react";
import { useMarketDemand } from "../../hooks/useFarming";
import { Spinner, PageError } from "../../components/Layout";

const SEASONS = [
  { value: "dry",       label: "Dry Season",  icon: "☀️",  months: "Nov – Mar" },
  { value: "wet",       label: "Wet Season",  icon: "🌧️",  months: "Apr – Oct" },
  { value: "harmattan", label: "Harmattan",   icon: "💨",  months: "Dec – Feb" },
];

const DEMAND_LEVEL = {
  high:   { width: "100%", color: "from-forest-500 to-gold-400" },
  medium: { width: "67%",  color: "from-blue-400 to-forest-400" },
  low:    { width: "33%",  color: "from-gray-300 to-gray-400" },
};

export default function MarketDemand() {
  const [season, setSeason] = useState("dry");
  const { data, isLoading, isError, refetch, isFetching } = useMarketDemand(season);

  return (
    <div className="space-y-6">
      <div className="bg-forest-600 text-white px-6 py-6 rounded-xl">
        <h1 className="text-2xl font-bold">📊 AI Market Demand Forecast</h1>
        <p className="text-forest-200 text-sm mt-1">
          Gemini AI analyses current supply listings to predict demand trends for Nigerian herbs.
        </p>
      </div>

      {/* Season selector */}
      <div className="card">
        <label className="label mb-3 block">Select Season</label>
        <div className="grid grid-cols-3 gap-3 mb-5">
          {SEASONS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setSeason(s.value)}
              className={`flex flex-col items-center gap-1 p-4 rounded-xl border-2 transition-all ${
                season === s.value
                  ? "border-forest-600 bg-forest-50 text-forest-700"
                  : "border-gray-200 hover:border-forest-300 text-gray-500"
              }`}
            >
              <span className="text-2xl">{s.icon}</span>
              <span className="text-sm font-semibold">{s.label}</span>
              <span className="text-xs text-gray-400">{s.months}</span>
            </button>
          ))}
        </div>
        <button
          className="btn-primary w-full flex items-center justify-center gap-2"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? <><Spinner /> Analysing market data…</> : "🤖 Generate AI Forecast →"}
        </button>
      </div>

      {isError && <PageError message="AI forecast failed. Ensure the backend is running." />}
      {isLoading && <div className="flex justify-center py-12"><Spinner /></div>}

      {data && (
        <div className="space-y-6">
          {/* Top herbs demand */}
          {data.top_herbs && data.top_herbs.length > 0 && (
            <div className="card">
              <h2 className="section-title mb-5">Herb Demand Overview</h2>
              <div className="space-y-5">
                {data.top_herbs.map((item) => {
                  const bar = DEMAND_LEVEL[item.demand_level] ?? DEMAND_LEVEL.low;
                  return (
                    <div key={item.herb_name}>
                      <div className="flex items-center justify-between text-sm mb-1.5">
                        <span className="font-medium text-gray-700">{item.herb_name}</span>
                        <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                          item.demand_level === "high" ? "bg-green-100 text-green-700" :
                          item.demand_level === "medium" ? "bg-blue-100 text-blue-700" :
                          "bg-gray-100 text-gray-600"
                        }`}>
                          {item.demand_level} demand
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2.5">
                        <div className={`h-2.5 rounded-full bg-gradient-to-r ${bar.color} transition-all duration-700`}
                          style={{ width: bar.width }} />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">{item.reasoning}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Planting recommendations */}
            {data.planting_recommendations && data.planting_recommendations.length > 0 && (
              <div className="card">
                <h2 className="section-title mb-4">🌱 Planting Recommendations</h2>
                <div className="space-y-3">
                  {data.planting_recommendations.map((rec, i) => (
                    <div key={i} className="bg-forest-50 border border-forest-100 rounded-lg p-3">
                      <p className="font-semibold text-forest-700 text-sm">{rec.herb_name}</p>
                      {rec.best_planting_months?.length > 0 && (
                        <p className="text-xs text-gray-600 mt-1">
                          🗓️ Best months: {rec.best_planting_months.join(", ")}
                        </p>
                      )}
                      {rec.regions?.length > 0 && (
                        <p className="text-xs text-gray-500">📍 {rec.regions.join(", ")}</p>
                      )}
                      {rec.notes && <p className="text-xs text-gray-600 mt-1">{rec.notes}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Price forecasts */}
            {data.price_forecasts && data.price_forecasts.length > 0 && (
              <div className="card">
                <h2 className="section-title mb-4">💰 Price Forecasts</h2>
                <div className="space-y-3">
                  {data.price_forecasts.map((fc, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                      <div>
                        <p className="font-medium text-sm text-gray-800">{fc.herb_name}</p>
                        {fc.current_avg_price_per_kg != null && (
                          <p className="text-xs text-gray-400">
                            Current: ₦{fc.current_avg_price_per_kg.toLocaleString()}/kg
                          </p>
                        )}
                      </div>
                      <div className="text-right ml-4">
                        {fc.forecast_price_per_kg != null && (
                          <p className="font-bold text-forest-600 text-sm">
                            ₦{fc.forecast_price_per_kg.toLocaleString()}/kg
                          </p>
                        )}
                        <p className={`text-xs font-medium ${
                          fc.trend === "up" ? "text-green-600" :
                          fc.trend === "down" ? "text-red-600" :
                          "text-gray-500"
                        }`}>
                          {fc.trend === "up" ? "↑" : fc.trend === "down" ? "↓" : "→"} {fc.trend}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Quality improvement tips */}
          {data.quality_improvement_tips && data.quality_improvement_tips.length > 0 && (
            <div className="card bg-forest-50 border-forest-200">
              <h2 className="font-semibold text-forest-700 mb-3">💡 Quality Improvement Tips</h2>
              <ul className="space-y-1.5">
                {data.quality_improvement_tips.map((tip, i) => (
                  <li key={i} className="text-sm text-forest-800 flex gap-2">
                    <span className="text-forest-400 shrink-0">•</span> {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
