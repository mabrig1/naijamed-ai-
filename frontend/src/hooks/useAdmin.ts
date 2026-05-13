import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { UserRole } from "../types";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AdminStats {
  total_herbs: number;
  total_users: number;
  total_formulations: number;
  published_formulations: number;
  total_trials: number;
  verified_trials: number;
  total_farm_listings: number;
  active_listings: number;
  total_patient_outcomes: number;
  total_compliance_docs: number;
}

export interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface ExportEngineStats {
  [key: string]: unknown;
}

export interface TopHerb {
  [key: string]: unknown;
}

export interface TopMarket {
  [key: string]: unknown;
}

export interface AdminUsersParams {
  role?: UserRole | "";
  is_active?: boolean | "";
  skip?: number;
  limit?: number;
}

// ── Query keys ────────────────────────────────────────────────────────────────

const KEYS = {
  stats: ["admin", "stats"] as const,
  users: (params: AdminUsersParams) => ["admin", "users", params] as const,
  exportStats: ["admin", "export", "stats"] as const,
  topHerbs: ["admin", "export", "top-herbs"] as const,
  topMarkets: ["admin", "export", "top-markets"] as const,
};

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useAdminStats() {
  return useQuery({
    queryKey: KEYS.stats,
    queryFn: async () => {
      const { data } = await api.get<AdminStats>("/api/admin/stats");
      return data;
    },
  });
}

export function useAdminUsers(params: AdminUsersParams = {}) {
  // Strip empty-string values so they are not sent as query params
  const cleanParams = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== "" && v !== undefined)
  );
  return useQuery({
    queryKey: KEYS.users(params),
    queryFn: async () => {
      const { data } = await api.get<AdminUser[]>("/api/admin/users", {
        params: cleanParams,
      });
      return data;
    },
  });
}

export function useChangeUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, role }: { id: number; role: UserRole }) => {
      const { data } = await api.patch<AdminUser>(`/api/admin/users/${id}/role`, {
        role,
      });
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await api.patch<AdminUser>(
        `/api/admin/users/${id}/deactivate`
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  });
}

export function useAdminExportStats() {
  return useQuery({
    queryKey: KEYS.exportStats,
    queryFn: async () => {
      const { data } = await api.get<ExportEngineStats>("/api/admin/export/stats");
      return data;
    },
  });
}

export function useAdminTopHerbs() {
  return useQuery({
    queryKey: KEYS.topHerbs,
    queryFn: async () => {
      const { data } = await api.get<TopHerb[]>("/api/admin/export/top-herbs");
      return data;
    },
  });
}

export function useAdminTopMarkets() {
  return useQuery({
    queryKey: KEYS.topMarkets,
    queryFn: async () => {
      const { data } = await api.get<TopMarket[]>("/api/admin/export/top-markets");
      return data;
    },
  });
}
