// ── Auth ────────────────────────────────────────────────────────────────────

export type UserRole = "farmer" | "researcher" | "pharma_company" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

// ── Herbs ───────────────────────────────────────────────────────────────────

export interface HerbCompound {
  id: number;
  herb_id: number;
  compound_name: string;
  chemical_formula: string | null;
  medicinal_use: string | null;
  source_study: string | null;
}

export interface Herb {
  id: number;
  name_english: string;
  scientific_name: string | null;
  name_igbo: string | null;
  name_yoruba: string | null;
  name_hausa: string | null;
  description: string | null;
  image_url: string | null;
  region_found: string | null;
  created_at: string;
}

export interface HerbDetail extends Herb {
  compounds: HerbCompound[];
}

export interface ActiveCompound {
  name: string;
  formula: string | null;
  role: string | null;
}

export interface ScanResponse {
  herb_name: string;
  scientific_name: string | null;
  medicinal_properties: string[];
  active_compounds: ActiveCompound[];
  diseases_treated: string[];
  drug_production_pathways: string[];
  research_gaps: string[];
  safety_warnings: string[];
}

export interface DrugSuggestionResponse {
  herb_name: string;
  scientific_name: string | null;
  target_disease: string;
  feasibility_score: number;
  mechanism_of_action: string;
  relevant_compounds: string[];
  production_pathway: string;
  clinical_trial_recommendations: string[];
  regulatory_considerations: string;
  estimated_timeline_years: string;
  risks: string[];
}

// ── Formulations ─────────────────────────────────────────────────────────────

export type FormulationType = "tablet" | "syrup" | "extract" | "capsule" | "cream";

export interface DrugFormulation {
  id: number;
  herb_id: number;
  created_by: number | null;
  formulation_type: FormulationType;
  target_disease: string | null;
  compound_used: string | null;
  dosage_suggestion: string | null;
  stability_prediction: string | null;
  side_effects_prediction: string | null;
  ai_notes: string | null;
  excipients_needed: string[] | null;
  manufacturing_process_summary: string | null;
  estimated_cost_savings_usd: number | null;
  next_steps: string[] | null;
  disclaimer: string | null;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface FormulationCompareResponse {
  formulation_id_1: number;
  formulation_id_2: number;
  recommended_id: number;
  reasoning: string;
  trade_offs: string[];
  combined_next_steps: string[];
}

// ── Farming ──────────────────────────────────────────────────────────────────

export interface HerbSummary {
  id: number;
  name_english: string;
  scientific_name: string | null;
}

export interface FarmerSummary {
  id: number;
  full_name: string;
}

export interface FarmListing {
  id: number;
  farmer_id: number;
  herb_id: number;
  herb: HerbSummary | null;
  farmer: FarmerSummary | null;
  quantity_kg: string;
  price_per_kg: string;
  location: string;
  harvest_date: string;
  quality_score: string | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface HerbDemandItem {
  herb_name: string;
  demand_level: "high" | "medium" | "low";
  reasoning: string;
}

export interface PlantingRecommendation {
  herb_name: string;
  best_planting_months: string[];
  regions: string[];
  notes: string;
}

export interface PriceForecast {
  herb_name: string;
  current_avg_price_per_kg: number | null;
  forecast_price_per_kg: number | null;
  trend: "up" | "down" | "stable";
}

export interface MarketDemandResponse {
  season: string;
  top_herbs: HerbDemandItem[];
  planting_recommendations: PlantingRecommendation[];
  price_forecasts: PriceForecast[];
  quality_improvement_tips: string[];
}

export interface InquiryResponse {
  listing_id: number;
  herb_name: string;
  farmer_name: string;
  message: string;
  quantity_kg_requested: string | null;
  status: string;
}

// ── Research ─────────────────────────────────────────────────────────────────

export type TrialStatus = "submitted" | "active" | "completed" | "withdrawn";

export interface ClinicalTrial {
  id: number;
  herb_id: number;
  researcher_id: number | null;
  herb: HerbSummary | null;
  study_title: string;
  study_phase: string | null;
  methodology: string | null;
  status: TrialStatus;
  start_date: string | null;
  end_date: string | null;
  patient_count: number | null;
  outcome_summary: string | null;
  effectiveness_score: string | null;
  findings: string | null;
  statistical_data: Record<string, unknown> | null;
  publication_doi: string | null;
  is_verified: boolean;
  ai_summary: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface TrialSummaryResponse {
  trial_id: number;
  plain_language_summary: string;
  statistical_significance: string;
  confidence_level: "low" | "medium" | "high";
  literature_comparison: string;
  recommended_next_steps: string[];
}

export type AgeGroup = "child" | "adult" | "elderly";
export type Sex = "male" | "female" | "not_disclosed";
export type OutcomeResult = "improved" | "no_change" | "worsened" | "adverse_reaction";

export interface PatientOutcome {
  id: number;
  herb_id: number;
  trial_id: number | null;
  age_group: AgeGroup;
  sex: Sex;
  condition_treated: string;
  dosage_used: string | null;
  duration_days: number | null;
  outcome: OutcomeResult;
  adverse_details: string | null;
  notes: string | null;
  created_at: string;
}

export interface EvidenceScoreResponse {
  herb_id: number;
  herb_name: string;
  evidence_score: number;
  verdict: "Promising" | "Needs more study" | "Not recommended";
  key_findings: string[];
  safety_signals: string[];
  trial_count: number;
  verified_trial_count: number;
}

// ── Compliance ────────────────────────────────────────────────────────────────

export type ComplianceStatus = "draft" | "submitted" | "approved" | "rejected";

export interface ComplianceDocument {
  id: number;
  user_id: number;
  herb_id: number;
  formulation_id: number | null;
  herb: HerbSummary | null;
  document_type: string;
  product_type: string | null;
  product_name: string | null;
  content_json: Record<string, unknown>;
  nafdac_stage: string | null;
  status: ComplianceStatus;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChecklistItem {
  step: number;
  title: string;
  description: string;
  required_documents: string[];
  estimated_time: string;
  tips: string[];
}

export interface ComplianceChecklistResponse {
  product_type: string;
  total_steps: number;
  items: ChecklistItem[];
}

export interface NafdacStage {
  stage_number: number;
  name: string;
  description: string;
  key_requirements: string[];
  typical_duration: string;
  fees_approximate: string;
}

export interface NafdacStagesResponse {
  total_stages: number;
  stages: NafdacStage[];
  general_notes: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  suggested_next_questions?: string[];
}

export interface ComplianceChatResponse {
  answer: string;
  disclaimer: string;
  suggested_next_questions: string[];
}

// ── Payments ──────────────────────────────────────────────────────────────────

export interface PaymentInitiateResponse {
  authorization_url: string;
  access_code: string;
  reference: string;
}

export interface PaymentVerifyResponse {
  reference: string;
  status: string;
  amount_kobo: number;
  currency: string;
  paid_at: string | null;
  customer_email: string | null;
  gateway_response: string | null;
}
