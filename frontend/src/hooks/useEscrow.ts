import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type EscrowStatus =
  | "held"
  | "delivery_confirmed"
  | "released"
  | "disputed"
  | "refunded"
  | "auto_released";

export interface EscrowTransaction {
  id: number;
  order_id: number;
  amount_usd: number;
  status: EscrowStatus;
  gateway: string | null;
  gateway_tx_id: string | null;
  gateway_transfer_id: string | null;
  gateway_payment_link: string | null;
  held_at: string;
  delivery_confirmed_at: string | null;
  auto_release_at: string | null;
  released_at: string | null;
  release_condition: string | null;
  dispute_reason: string | null;
  dispute_raised_at: string | null;
  dispute_resolved_at: string | null;
  ai_recommendation: string | null;
  resolution_notes: string | null;
}

export interface EscrowHoldResponse {
  escrow_id: number;
  order_id: number;
  amount_usd: number;
  gateway: string;
  status: EscrowStatus;
  payment_link: string | null;
  stripe_client_secret: string | null;
  stripe_payment_intent_id: string | null;
  auto_release_at: string;
  message: string;
}

export interface EscrowStatusResponse {
  order_id: number;
  escrow_id: number;
  amount_usd: number;
  status: EscrowStatus;
  gateway: string | null;
  held_at: string;
  auto_release_at: string | null;
  delivery_confirmed_at: string | null;
  released_at: string | null;
  dispute_raised_at: string | null;
  dispute_window_open: boolean;
  days_until_auto_release: number | null;
}

export interface EscrowReleaseResponse {
  order_id: number;
  escrow_id: number;
  status: EscrowStatus;
  released_at: string;
  transfer_id: string | null;
  transfer_status: string | null;
  message: string;
}

export interface DisputeListItem {
  escrow_id: number;
  order_id: number;
  amount_usd: number;
  dispute_reason: string | null;
  dispute_raised_at: string | null;
  dispute_resolved_at: string | null;
  ai_recommendation_summary: string | null;
  resolution_notes: string | null;
  gateway: string | null;
  status: EscrowStatus;
}

export interface DisputeResolveResponse {
  escrow_id: number;
  order_id: number;
  resolution: string;
  status: EscrowStatus;
  resolved_at: string;
  transfer_id: string | null;
  ai_recommendation: Record<string, unknown> | null;
  message: string;
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  myTransactions: ["escrow-transactions"],
  status: (orderId: number) => ["escrow-status", orderId],
  disputes: ["escrow-disputes"],
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useMyEscrowTransactions() {
  return useQuery({
    queryKey: KEYS.myTransactions,
    queryFn: async () => {
      const { data } = await api.get<{ user_id: number; count: number; transactions: EscrowTransaction[] }>(
        "/api/escrow/my-transactions"
      );
      return data;
    },
  });
}

export function useEscrowStatus(orderId: number) {
  return useQuery({
    queryKey: KEYS.status(orderId),
    queryFn: async () => {
      const { data } = await api.get<EscrowStatusResponse>(
        `/api/escrow/status/${orderId}`
      );
      return data;
    },
    enabled: !!orderId,
    refetchInterval: 30_000,
  });
}

export function useHoldEscrow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      order_id: number;
      gateway?: "flutterwave" | "stripe";
      currency?: string;
      redirect_url?: string;
      buyer_email?: string;
    }) => {
      const { data } = await api.post<EscrowHoldResponse>("/api/escrow/hold", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.myTransactions }),
  });
}

export function useReleaseEscrow() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      order_id: number;
      seller_bank_code?: string;
      seller_account_number?: string;
      seller_stripe_account_id?: string;
      confirmation_note?: string;
    }) => {
      const { order_id, ...rest } = body;
      const { data } = await api.post<EscrowReleaseResponse>(
        `/api/escrow/release/${order_id}`,
        rest
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.myTransactions });
      qc.invalidateQueries({ queryKey: ["escrow-status"] });
    },
  });
}

export function useRaiseDispute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      order_id: number;
      reason: string;
      details?: string;
    }) => {
      const { order_id, ...rest } = body;
      const { data } = await api.post<{
        order_id: number;
        escrow_id: number;
        status: EscrowStatus;
        dispute_raised_at: string;
        dispute_deadline: string;
        message: string;
      }>(`/api/escrow/dispute/${order_id}`, rest);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.myTransactions });
      qc.invalidateQueries({ queryKey: KEYS.disputes });
    },
  });
}

export function useDisputes() {
  return useQuery({
    queryKey: KEYS.disputes,
    queryFn: async () => {
      const { data } = await api.get<{ count: number; disputes: DisputeListItem[] }>(
        "/api/escrow/disputes"
      );
      return data;
    },
  });
}

export function useResolveDispute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      escrow_id: number;
      resolution: "release_to_seller" | "refund_to_buyer" | "split_settlement";
      resolution_notes: string;
      compensation_amount_usd?: number;
    }) => {
      const { escrow_id, ...rest } = body;
      const { data } = await api.post<DisputeResolveResponse>(
        `/api/escrow/disputes/${escrow_id}/resolve`,
        rest
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.disputes });
      qc.invalidateQueries({ queryKey: KEYS.myTransactions });
    },
  });
}
