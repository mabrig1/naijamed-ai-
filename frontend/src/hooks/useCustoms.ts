import { useQuery, useMutation } from "@tanstack/react-query";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface HSCodeResult {
  hs_code: string;
  description: string;
  duty_rate: string | null;
  vat_applicable: boolean;
  prohibited_countries: string[];
  required_permits: string[];
  notes: string;
}

export interface CountryRequirements {
  country: string;
  flag_emoji: string;
  required_documents: string[];
  phytosanitary_required: boolean;
  organic_certification_accepted: string[];
  import_duty_range: string;
  prohibited_herbs: string[];
  special_notes: string;
  last_updated: string;
}

export interface NEPCGuide {
  title: string;
  overview: string;
  registration_steps: Array<{ step: number; title: string; requirements: string[]; timeline: string }>;
  fees: Record<string, string>;
  contact: Record<string, string>;
  tips: string[];
}

export interface CBNRepatriation {
  title: string;
  overview: string;
  timeline: string;
  penalties: string[];
  forex_accounts: string[];
  payment_instruments: string[];
  tips: string[];
  key_contacts: Record<string, string>;
}

export interface TradeRestriction {
  herb_name: string;
  restriction_type: "banned" | "controlled" | "permit_required" | "quota";
  countries_affected: string[];
  reason: string;
  alternative: string | null;
}

export interface CustomsChatMessage {
  role: "user" | "assistant";
  content: string;
  suggested_questions?: string[];
}

export interface CustomsChatResponse {
  answer: string;
  hs_code_mentioned: string | null;
  country_mentioned: string | null;
  disclaimer: string;
  suggested_questions: string[];
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  restrictions: ["customs-restrictions"],
  countryReqs: (country: string) => ["customs-country", country],
  nepcGuide: ["nepc-guide"],
  cbnRepatriation: ["cbn-repatriation"],
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useTradeRestrictions() {
  return useQuery({
    queryKey: KEYS.restrictions,
    queryFn: async () => {
      const { data } = await api.get<TradeRestriction[]>("/api/customs/restrictions");
      return data;
    },
    staleTime: 1000 * 60 * 60, // 1 hour — regulatory data changes rarely
  });
}

export function useCountryRequirements(country: string) {
  return useQuery({
    queryKey: KEYS.countryReqs(country),
    queryFn: async () => {
      const { data } = await api.get<CountryRequirements>(
        `/api/customs/requirements/${country}`
      );
      return data;
    },
    enabled: !!country,
    staleTime: 1000 * 60 * 60,
  });
}

export function useNEPCGuide() {
  return useQuery({
    queryKey: KEYS.nepcGuide,
    queryFn: async () => {
      const { data } = await api.get<NEPCGuide>("/api/customs/nepc-guide");
      return data;
    },
    staleTime: 1000 * 60 * 60 * 6,
  });
}

export function useCBNRepatriation() {
  return useQuery({
    queryKey: KEYS.cbnRepatriation,
    queryFn: async () => {
      const { data } = await api.get<CBNRepatriation>("/api/customs/cbn-repatriation");
      return data;
    },
    staleTime: 1000 * 60 * 60 * 6,
  });
}

export function useHSLookup() {
  return useMutation({
    mutationFn: async (herbName: string) => {
      const { data } = await api.post<HSCodeResult>("/api/customs/hs-lookup", {
        herb_name: herbName,
      });
      return data;
    },
  });
}

export function useCustomsChat() {
  return useMutation({
    mutationFn: async (params: {
      message: string;
      history: Array<{ role: string; content: string }>;
    }) => {
      const { data } = await api.post<CustomsChatResponse>("/api/customs/chat", params);
      return data;
    },
  });
}

export function useFormMGuide() {
  return useQuery({
    queryKey: ["form-m-guide"],
    queryFn: async () => {
      const { data } = await api.get<Record<string, unknown>>("/api/customs/form-m");
      return data;
    },
    staleTime: 1000 * 60 * 60 * 12,
  });
}
