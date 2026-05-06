import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface ExportListing {
  id: number;
  seller_id: number;
  herb_id: number;
  herb_name: string;
  scientific_name: string | null;
  grade: "A" | "B" | "C" | "organic";
  quantity_kg: number;
  price_per_kg_usd: number;
  origin_state: string;
  destination_countries: string[];
  freight_channels: string[];
  hs_code: string | null;
  nafdac_cert_url: string | null;
  nepc_cert_url: string | null;
  naqs_cert_url: string | null;
  is_organic: boolean;
  seller_rating: number | null;
  certifications: string[];
  description: string | null;
  images: string[];
  status: "active" | "draft" | "sold" | "expired";
  created_at: string;
  updated_at: string;
}

export interface ExportListingDetail extends ExportListing {
  gps_lat: number | null;
  gps_lng: number | null;
  seller_name: string;
  seller_verified: boolean;
  ai_buyer_matches: BuyerMatch[];
}

export interface BuyerMatch {
  buyer_id: number;
  buyer_name: string;
  country: string;
  match_score: number;
  preferred_herbs: string[];
  monthly_volume_kg: number;
  incoterms: string[];
}

export interface GlobalBuyer {
  id: number;
  user_id: number;
  company_name: string;
  country: string;
  preferred_herbs: string[];
  monthly_volume_kg: number;
  preferred_incoterms: string[];
  certifications_required: string[];
  contact_email: string;
  verified: boolean;
  ai_recommendations: ExportListing[];
  created_at: string;
}

export interface FreightQuote {
  id: number;
  order_id: number | null;
  listing_id: number;
  origin_state: string;
  destination_country: string;
  quantity_kg: number;
  air_freight_usd: number | null;
  sea_freight_usd: number | null;
  road_freight_usd: number | null;
  ecommerce_usd: number | null;
  ai_recommendation: string | null;
  breakdown: FreightBreakdown | null;
  created_at: string;
}

export interface FreightBreakdown {
  air: FreightOption | null;
  sea: FreightOption | null;
  road: FreightOption | null;
  ecommerce: FreightOption | null;
}

export interface FreightOption {
  total_usd: number;
  freight_usd: number;
  insurance_usd: number;
  handling_usd: number;
  transit_days: number;
  notes: string;
  recommended: boolean;
}

export interface TradeInquiry {
  listing_id: number;
  message: string;
  quantity_kg?: number;
  target_price_usd?: number;
  contact_email?: string;
}

export interface HSCodeResponse {
  hs_code: string;
  description: string;
  duty_rate: string | null;
  notes: string;
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  listings: (p: object) => ["export-listings", p],
  listing: (id: number) => ["export-listing", id],
  myListings: ["export-listings", "mine"],
  buyers: (p: object) => ["global-buyers", p],
  buyer: (id: number) => ["global-buyer", id],
  myBuyerProfile: ["global-buyer", "me"],
  freightQuotes: (listingId: number) => ["freight-quotes", listingId],
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useExportListings(params?: {
  herb_id?: number;
  grade?: string;
  country?: string;
  is_organic?: boolean;
  min_price?: number;
  max_price?: number;
  freight_channel?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: KEYS.listings(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<ExportListing[]>("/api/export/listings", { params });
      return data;
    },
  });
}

export function useExportListingDetail(id: number) {
  return useQuery({
    queryKey: KEYS.listing(id),
    queryFn: async () => {
      const { data } = await api.get<ExportListingDetail>(`/api/export/listings/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useMyExportListings() {
  return useQuery({
    queryKey: KEYS.myListings,
    queryFn: async () => {
      const { data } = await api.get<ExportListing[]>("/api/export/my-listings");
      return data;
    },
  });
}

export function useCreateExportListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: FormData) => {
      const { data } = await api.post<ExportListing>("/api/export/listings", body, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["export-listings"] }),
  });
}

export function useSendTradeInquiry() {
  return useMutation({
    mutationFn: async (body: TradeInquiry) => {
      const { data } = await api.post<{ message: string }>("/api/export/inquire", body);
      return data;
    },
  });
}

export function useHSCodeLookup() {
  return useMutation({
    mutationFn: async (herbName: string) => {
      const { data } = await api.post<HSCodeResponse>("/api/customs/hs-lookup", {
        herb_name: herbName,
      });
      return data;
    },
  });
}

export function useFreightQuotes(listingId: number) {
  return useQuery({
    queryKey: KEYS.freightQuotes(listingId),
    queryFn: async () => {
      const { data } = await api.get<FreightQuote[]>(
        `/api/logistics/freight-quotes?listing_id=${listingId}`
      );
      return data;
    },
    enabled: !!listingId,
  });
}

export function useCalculateFreight() {
  return useMutation({
    mutationFn: async (body: {
      herb_type: string;
      origin_state: string;
      destination_country: string;
      quantity_kg: number;
    }) => {
      const { data } = await api.post<FreightQuote>("/api/logistics/calculate-freight", body);
      return data;
    },
  });
}

export function useGlobalBuyers(params?: { country?: string; herb?: string }) {
  return useQuery({
    queryKey: KEYS.buyers(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<GlobalBuyer[]>("/api/export/buyers", { params });
      return data;
    },
  });
}

export function useMyBuyerProfile() {
  return useQuery({
    queryKey: KEYS.myBuyerProfile,
    queryFn: async () => {
      const { data } = await api.get<GlobalBuyer>("/api/export/buyers/me");
      return data;
    },
    retry: false,
  });
}

export function useCreateOrUpdateBuyerProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<GlobalBuyer>) => {
      const { data } = await api.post<GlobalBuyer>("/api/export/buyers/register", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.myBuyerProfile }),
  });
}
