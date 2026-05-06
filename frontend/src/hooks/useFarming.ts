import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { FarmListing, MarketDemandResponse, InquiryResponse } from "../types";

const KEYS = {
  listings: (p: object) => ["listings", p],
  myListings: ["listings", "mine"],
  demand: (season: string) => ["market-demand", season],
};

export function useFarmListings(params?: {
  herb_id?: number;
  location?: string;
  quality?: string;
  min_price?: number;
  max_price?: number;
  available_only?: boolean;
}) {
  return useQuery({
    queryKey: KEYS.listings(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<FarmListing[]>("/api/farming/listings", { params });
      return data;
    },
  });
}

export function useMyListings(params?: { is_available?: boolean }) {
  return useQuery({
    queryKey: [...KEYS.myListings, params],
    queryFn: async () => {
      const { data } = await api.get<FarmListing[]>("/api/farming/my-listings", { params });
      return data;
    },
  });
}

export function useMarketDemand(season: string) {
  return useQuery({
    queryKey: KEYS.demand(season),
    queryFn: async () => {
      const { data } = await api.get<MarketDemandResponse>("/api/farming/market-demand", {
        params: { season },
      });
      return data;
    },
    enabled: false,
  });
}

export function useCreateListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      quantity_kg: number;
      price_per_kg: number;
      location: string;
      quality_grade?: "premium" | "standard" | "economy";
      harvest_date?: string;
      description?: string;
    }) => {
      const { data } = await api.post<FarmListing>("/api/farming/listings", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listings"] }),
  });
}

export function useDeleteListing() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/api/farming/listings/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["listings"] }),
  });
}

export function useInquireListing() {
  return useMutation({
    mutationFn: async (params: {
      listingId: number;
      message: string;
      contact_email?: string;
      quantity_kg_requested?: number;
    }) => {
      const { listingId, ...body } = params;
      const { data } = await api.post<InquiryResponse>(
        `/api/farming/listings/${listingId}/inquire`,
        body
      );
      return data;
    },
  });
}
