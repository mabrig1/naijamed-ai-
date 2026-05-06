import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type MarketRegion = "europe" | "north_america" | "asia" | "middle_east" | "africa";

export interface PriceIndexItem {
  herb_id: number;
  herb_name: string;
  region: MarketRegion;
  price_per_kg_usd: number;
  trend: "up" | "down" | "stable";
  change_pct_30d: number;
  recorded_date: string;
  source: string;
}

export interface PriceIndexResponse {
  count: number;
  items: PriceIndexItem[];
  as_of: string;
}

export interface HerbPriceHistory {
  herb_id: number;
  herb_name: string;
  region: MarketRegion;
  prices: Array<{ date: string; price_per_kg_usd: number }>;
}

export interface PriceForecastResponse {
  herb_id: number;
  herb_name: string;
  region: MarketRegion;
  current_avg_price_usd: number;
  forecast_30d: number;
  forecast_90d: number;
  trend: "up" | "down" | "stable";
  confidence: "high" | "medium" | "low";
  drivers: string[];
  risks: string[];
  recommendation: string;
  projection_points: Array<{ date: string; price: number; projected: boolean }>;
}

export interface BestTimeToSellResponse {
  herb_id: number;
  herb_name: string;
  best_market: MarketRegion;
  best_window_days: number;
  reasoning: string;
  second_best: MarketRegion;
  markets_to_avoid: MarketRegion[];
  optimal_quantity_allocation_kg: Record<string, number>;
  net_return_per_kg_usd: number;
}

export interface PriceCompareResponse {
  herb_id: number;
  herb_name: string;
  regions: Array<{
    region: MarketRegion;
    price_per_kg_usd: number;
    trend: "up" | "down" | "stable";
    change_pct: number;
  }>;
}

export interface AlertSubscription {
  id: string;
  herb_id: number;
  herb_name: string;
  threshold_usd: number;
  alert_when: "above" | "below";
  active: boolean;
  created_at: string;
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  index: (p: object) => ["price-index", p],
  herbPrices: (herbId: number, region?: string) => ["herb-prices", herbId, region],
  forecast: (herbId: number, region: string) => ["price-forecast", herbId, region],
  compare: (herbId: number) => ["price-compare", herbId],
  bestTime: (herbId: number) => ["best-time", herbId],
  alerts: ["price-alerts"],
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function usePriceIndex(params?: {
  region?: MarketRegion;
  herb_id?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: KEYS.index(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<PriceIndexResponse>("/api/prices/index", { params });
      return data;
    },
    refetchInterval: 1000 * 60 * 5, // refresh every 5 min
  });
}

export function useHerbPriceHistory(herbId: number, region?: MarketRegion) {
  return useQuery({
    queryKey: KEYS.herbPrices(herbId, region),
    queryFn: async () => {
      const { data } = await api.get<HerbPriceHistory>(
        `/api/prices/herb/${herbId}`,
        { params: region ? { region } : undefined }
      );
      return data;
    },
    enabled: !!herbId,
  });
}

export function usePriceForecast(herbId: number, region: MarketRegion) {
  return useQuery({
    queryKey: KEYS.forecast(herbId, region),
    queryFn: async () => {
      const { data } = await api.get<PriceForecastResponse>("/api/prices/forecast", {
        params: { herb_id: herbId, region },
      });
      return data;
    },
    enabled: !!herbId && !!region,
    staleTime: 1000 * 60 * 30, // AI forecasts stale after 30 min
  });
}

export function usePriceCompare(herbId: number) {
  return useQuery({
    queryKey: KEYS.compare(herbId),
    queryFn: async () => {
      const { data } = await api.get<PriceCompareResponse>("/api/prices/compare", {
        params: { herb_id: herbId },
      });
      return data;
    },
    enabled: !!herbId,
  });
}

export function useBestTimeToSell(herbId: number) {
  return useQuery({
    queryKey: KEYS.bestTime(herbId),
    queryFn: async () => {
      const { data } = await api.get<BestTimeToSellResponse>("/api/prices/best-time-to-sell", {
        params: { herb_id: herbId },
      });
      return data;
    },
    enabled: !!herbId,
    staleTime: 1000 * 60 * 30,
  });
}

export function usePriceAlerts() {
  return useQuery({
    queryKey: KEYS.alerts,
    queryFn: async () => {
      const { data } = await api.get<AlertSubscription[]>("/api/prices/alerts");
      return data;
    },
  });
}

export function useSubscribePriceAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      threshold_usd: number;
      alert_when: "above" | "below";
    }) => {
      const { data } = await api.post<AlertSubscription>(
        "/api/prices/alerts/subscribe",
        body
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.alerts }),
  });
}

export function useSubmitPrice() {
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      region: MarketRegion;
      price_per_kg_usd: number;
      source?: string;
    }) => {
      const { data } = await api.post<{ message: string }>("/api/prices/submit", body);
      return data;
    },
  });
}
