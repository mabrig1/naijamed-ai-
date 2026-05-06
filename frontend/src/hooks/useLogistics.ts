import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Shipment {
  id: number;
  order_id: number;
  tracking_number: string;
  carrier: string | null;
  freight_channel: "air" | "sea" | "road" | "ecommerce";
  origin_state: string;
  destination_country: string;
  status: "pending" | "in_transit" | "customs_hold" | "delivered" | "returned";
  is_cold_chain: boolean;
  weight_kg: number | null;
  estimated_delivery: string | null;
  actual_delivery: string | null;
  events: ShipmentEvent[];
  documents: ExportDocument[];
  temperature_log: TemperatureReading[] | null;
  created_at: string;
  updated_at: string;
}

export interface ShipmentEvent {
  id: number;
  shipment_id: number;
  event_type: string;
  location: string | null;
  description: string;
  timestamp: string;
}

export interface ExportDocument {
  id: number;
  order_id: number;
  document_type: "invoice" | "packing_list" | "coo" | "customs_declaration" | "phytosanitary" | "other";
  file_url: string | null;
  ai_generated: boolean;
  content_json: Record<string, unknown> | null;
  verified: boolean;
  created_at: string;
}

export interface FreightQuoteResult {
  id: number;
  herb_type: string;
  origin_state: string;
  destination_country: string;
  quantity_kg: number;
  air: FreightOption | null;
  sea: FreightOption | null;
  road: FreightOption | null;
  ecommerce: FreightOption | null;
  ai_recommendation: "air" | "sea" | "road" | "ecommerce" | null;
  ai_reasoning: string | null;
  created_at: string;
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

export interface TemperatureReading {
  timestamp: string;
  celsius: number;
  alert: boolean;
}

export interface GenerateDocumentRequest {
  order_id: number;
  document_type: "invoice" | "packing_list" | "coo" | "customs_declaration";
  extra_data?: Record<string, unknown>;
}

// ── Query keys ───────────────────────────────────────────────────────────────

const KEYS = {
  shipments: ["shipments"],
  shipment: (id: number) => ["shipment", id],
  shipmentByOrder: (orderId: number) => ["shipment-order", orderId],
  documents: (orderId: number) => ["export-docs", orderId],
  allDocuments: ["export-docs"],
};

// ── Hooks ────────────────────────────────────────────────────────────────────

export function useMyShipments() {
  return useQuery({
    queryKey: KEYS.shipments,
    queryFn: async () => {
      const { data } = await api.get<Shipment[]>("/api/logistics/my-shipments");
      return data;
    },
  });
}

export function useShipmentDetail(id: number) {
  return useQuery({
    queryKey: KEYS.shipment(id),
    queryFn: async () => {
      const { data } = await api.get<Shipment>(`/api/logistics/shipments/${id}`);
      return data;
    },
    enabled: !!id,
    refetchInterval: 30_000, // poll every 30s for live tracking
  });
}

export function useShipmentByOrder(orderId: number) {
  return useQuery({
    queryKey: KEYS.shipmentByOrder(orderId),
    queryFn: async () => {
      const { data } = await api.get<Shipment>(
        `/api/logistics/shipments/by-order/${orderId}`
      );
      return data;
    },
    enabled: !!orderId,
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
      const { data } = await api.post<FreightQuoteResult>(
        "/api/logistics/calculate-freight",
        body
      );
      return data;
    },
  });
}

export function useBookFreight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {
      quote_id: number;
      channel: "air" | "sea" | "road" | "ecommerce";
      order_id: number;
    }) => {
      const { data } = await api.post<Shipment>("/api/logistics/book-freight", body);
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEYS.shipments }),
  });
}

export function useExportDocuments(orderId: number) {
  return useQuery({
    queryKey: KEYS.documents(orderId),
    queryFn: async () => {
      const { data } = await api.get<ExportDocument[]>(
        `/api/logistics/documents?order_id=${orderId}`
      );
      return data;
    },
    enabled: !!orderId,
  });
}

export function useAllExportDocuments() {
  return useQuery({
    queryKey: KEYS.allDocuments,
    queryFn: async () => {
      const { data } = await api.get<ExportDocument[]>("/api/logistics/documents");
      return data;
    },
  });
}

export function useGenerateDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: GenerateDocumentRequest) => {
      const { data } = await api.post<ExportDocument>(
        "/api/logistics/documents/generate",
        body
      );
      return data;
    },
    onSuccess: (_, vars) =>
      qc.invalidateQueries({ queryKey: KEYS.documents(vars.order_id) }),
  });
}

export function useUploadDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      orderId,
      formData,
    }: {
      orderId: number;
      formData: FormData;
    }) => {
      const { data } = await api.post<ExportDocument>(
        `/api/logistics/documents/upload?order_id=${orderId}`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return data;
    },
    onSuccess: (doc) =>
      qc.invalidateQueries({ queryKey: KEYS.documents(doc.order_id) }),
  });
}
