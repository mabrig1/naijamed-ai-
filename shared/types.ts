// Shared domain types — kept in sync with backend Pydantic schemas

export type UserRole = "farmer" | "researcher" | "pharma_company" | "admin";

export type FormulationType = "tablet" | "syrup" | "extract" | "capsule" | "cream";

export type SubscriptionPlan = "free" | "basic" | "professional" | "enterprise";

export type ComplianceStatus = "draft" | "submitted" | "approved" | "rejected";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Herb {
  id: number;
  name_english: string;
  name_igbo?: string;
  name_yoruba?: string;
  name_hausa?: string;
  description?: string;
  image_url?: string;
  region_found?: string;
  created_at: string;
}

export interface HerbCompound {
  id: number;
  herb_id: number;
  compound_name: string;
  chemical_formula?: string;
  medicinal_use?: string;
  source_study?: string;
}

export interface FarmListing {
  id: number;
  farmer_id: number;
  herb_id: number;
  quantity_kg: number;
  price_per_kg: number;
  location: string;
  harvest_date: string;
  quality_score?: number;
  is_available: boolean;
}

export interface DrugFormulation {
  id: number;
  herb_id: number;
  created_by: number;
  formulation_type: FormulationType;
  dosage_suggestion?: string;
  stability_prediction?: string;
  side_effects_prediction?: string;
  ai_notes?: string;
  created_at: string;
}

export interface ClinicalTrial {
  id: number;
  herb_id: number;
  researcher_id: number;
  study_title: string;
  patient_count?: number;
  outcome_summary?: string;
  effectiveness_score?: number;
  is_verified: boolean;
  created_at: string;
}

export interface ComplianceDocument {
  id: number;
  user_id: number;
  herb_id: number;
  document_type: string;
  content_json: Record<string, unknown>;
  nafdac_stage?: string;
  submitted_at?: string;
  status: ComplianceStatus;
}

export interface Subscription {
  id: number;
  user_id: number;
  plan: SubscriptionPlan;
  start_date: string;
  end_date?: string;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}
