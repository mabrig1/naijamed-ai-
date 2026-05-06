import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type {
  ClinicalTrial, TrialSummaryResponse, PatientOutcome, EvidenceScoreResponse, TrialStatus,
} from "../types";

const KEYS = {
  trials: (p: object) => ["trials", p],
  trial: (id: number) => ["trials", id],
  outcomes: (p: object) => ["outcomes", p],
  evidence: (herbId: number) => ["evidence", herbId],
};

export function useTrialList(params?: {
  herb_id?: number;
  status?: TrialStatus;
  min_effectiveness?: number;
  verified_only?: boolean;
}) {
  return useQuery({
    queryKey: KEYS.trials(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<ClinicalTrial[]>("/api/research/trials", { params });
      return data;
    },
  });
}

export function useTrialDetail(id: number) {
  return useQuery({
    queryKey: KEYS.trial(id),
    queryFn: async () => {
      const { data } = await api.get<ClinicalTrial>(`/api/research/trials/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useTrialAISummary() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.get<TrialSummaryResponse>(`/api/research/trials/${id}/ai-summary`);
      return data;
    },
    onSuccess: (_data, id) => qc.invalidateQueries({ queryKey: KEYS.trial(id) }),
  });
}

export function useSubmitTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      title: string;
      abstract?: string;
      study_phase?: string;
      methodology?: string;
      start_date?: string;
      end_date?: string;
      patient_count?: number;
      findings?: string;
      publication_doi?: string;
    }) => {
      const { data } = await api.post<ClinicalTrial>("/api/research/trials", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trials"] }),
  });
}

export function useVerifyTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.post<ClinicalTrial>(`/api/research/trials/${id}/verify`);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["trials"] }),
  });
}

export function useOutcomeList(params?: { herb_id?: number; outcome?: string }) {
  return useQuery({
    queryKey: KEYS.outcomes(params ?? {}),
    queryFn: async () => {
      const { data } = await api.get<PatientOutcome[]>("/api/research/outcomes", { params });
      return data;
    },
  });
}

export function useLogOutcome() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      herb_id: number;
      trial_id?: number;
      age_group: string;
      sex: string;
      condition_treated: string;
      outcome: string;
      dosage_used?: string;
      duration_days?: number;
      adverse_details?: string;
      notes?: string;
    }) => {
      const { data } = await api.post<PatientOutcome>("/api/research/outcomes", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outcomes"] }),
  });
}

export function useHerbEvidence(herbId: number) {
  return useQuery({
    queryKey: KEYS.evidence(herbId),
    queryFn: async () => {
      const { data } = await api.get<EvidenceScoreResponse>(
        `/api/research/herbs/${herbId}/evidence`
      );
      return data;
    },
    enabled: !!herbId,
  });
}
