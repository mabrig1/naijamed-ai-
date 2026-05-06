import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type {
  ComplianceDocument, ComplianceChecklistResponse, NafdacStagesResponse,
  ComplianceChatResponse, ComplianceStatus,
} from "../types";

const KEYS = {
  docs: (p: object) => ["compliance-docs", p],
  doc: (id: number) => ["compliance-docs", id],
  checklist: (pt: string) => ["checklist", pt],
  stages: ["nafdac-stages"],
};

export function useComplianceDocuments(params?: {
  herb_id?: number;
  status?: ComplianceStatus;
}) {
  return useQuery({
    queryKey: KEYS.docs(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<ComplianceDocument[]>("/api/compliance/documents", {
        params,
      });
      return data;
    },
  });
}

export function useComplianceDocument(id: number) {
  return useQuery({
    queryKey: KEYS.doc(id),
    queryFn: async () => {
      const { data } = await api.get<ComplianceDocument>(`/api/compliance/documents/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateComplianceDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id?: number;
      document_type: string;
      product_type?: string;
      product_name?: string;
      formulation_id?: number;
      nafdac_stage?: string;
    }) => {
      const { data } = await api.post<ComplianceDocument>("/api/compliance/documents", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-docs"] }),
  });
}

export function useGenerateComplianceDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<ComplianceDocument>(
        `/api/compliance/documents/${id}/generate`,
        {}
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-docs"] }),
  });
}

export function useSubmitComplianceDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post(`/api/compliance/documents/${id}/submit`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["compliance-docs"] }),
  });
}

export function useNafdacChecklist(productType: string) {
  return useQuery({
    queryKey: KEYS.checklist(productType),
    queryFn: async () => {
      const { data } = await api.get<ComplianceChecklistResponse>("/api/compliance/checklist", {
        params: { product_type: productType },
      });
      return data.items ?? [];
    },
    enabled: !!productType,
  });
}

export function useNafdacStages(_productType?: string) {
  return useQuery({
    queryKey: KEYS.stages,
    queryFn: async () => {
      const { data } = await api.get<NafdacStagesResponse>("/api/compliance/stages");
      return data;
    },
  });
}

export function useComplianceChat() {
  return useMutation({
    mutationFn: async (body: { question: string; context?: string }) => {
      const { data } = await api.post<ComplianceChatResponse>("/api/compliance/chat", body);
      return data;
    },
  });
}
