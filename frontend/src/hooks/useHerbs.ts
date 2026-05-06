import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Herb, HerbDetail, ScanResponse, DrugSuggestionResponse } from "../types";

const KEYS = {
  list: (p: object) => ["herbs", p],
  detail: (id: number) => ["herbs", id],
};

export function useHerbList(params?: {
  search?: string;
  region?: string;
  compound?: string;
  skip?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: KEYS.list(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<Herb[]>("/api/herbs", { params });
      return data;
    },
  });
}

export function useHerbDetail(id: number) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: async () => {
      const { data } = await api.get<HerbDetail>(`/api/herbs/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useScanHerb() {
  return useMutation({
    mutationFn: async (body: { herb_name: string; user_description?: string }) => {
      const { data } = await api.post<ScanResponse>("/api/herbs/scan", body);
      return data;
    },
  });
}

export function useDrugSuggestion(herbId: number) {
  return useMutation({
    mutationFn: async (body: { target_disease: string }) => {
      const { data } = await api.post<DrugSuggestionResponse>(
        `/api/herbs/${herbId}/drug-suggestion`,
        body
      );
      return data;
    },
  });
}

export function useCreateHerb() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<Herb>) => {
      const { data } = await api.post<HerbDetail>("/api/herbs", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["herbs"] }),
  });
}
