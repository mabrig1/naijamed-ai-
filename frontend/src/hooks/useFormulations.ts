import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { DrugFormulation, FormulationCompareResponse, FormulationType } from "../types";

const KEYS = {
  list: (p: object) => ["formulations", p],
  detail: (id: number) => ["formulations", id],
};

export function useFormulationList(params?: {
  herb_id?: number;
  formulation_type?: FormulationType;
  published_only?: boolean;
}) {
  return useQuery({
    queryKey: KEYS.list(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<DrugFormulation[]>("/api/formulations", { params });
      return data;
    },
  });
}

export function useFormulationDetail(id: number) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: async () => {
      const { data } = await api.get<DrugFormulation>(`/api/formulations/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useGenerateFormulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      target_disease: string;
      compound_used?: string;
      formulation_type: FormulationType;
    }) => {
      const { data } = await api.post<DrugFormulation>("/api/formulations/generate", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["formulations"] }),
  });
}

export function usePublishFormulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<DrugFormulation>(`/api/formulations/${id}/publish`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["formulations"] }),
  });
}

export function useCompareFormulations() {
  return useMutation({
    mutationFn: async (body: { formulation_id_1: number; formulation_id_2: number }) => {
      const { data } = await api.post<FormulationCompareResponse>(
        "/api/formulations/compare",
        body
      );
      return data;
    },
  });
}
