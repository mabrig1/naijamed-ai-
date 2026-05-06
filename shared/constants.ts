export const USER_ROLES = ["farmer", "researcher", "pharma_company", "admin"] as const;

export const FORMULATION_TYPES = ["tablet", "syrup", "extract", "capsule", "cream"] as const;

export const SUBSCRIPTION_PLANS = ["free", "basic", "professional", "enterprise"] as const;

export const COMPLIANCE_STATUSES = ["draft", "submitted", "approved", "rejected"] as const;

export const NAFDAC_STAGES = [
  "pre_submission",
  "dossier_review",
  "laboratory_analysis",
  "plant_inspection",
  "approval",
] as const;

export const NIGERIAN_REGIONS = [
  "North Central",
  "North East",
  "North West",
  "South East",
  "South South",
  "South West",
] as const;

export const API_ROUTES = {
  AUTH_LOGIN: "/auth/login",
  AUTH_REGISTER: "/auth/register",
  HERBS: "/herbs",
  COMPOUNDS: "/compounds",
  FARM_LISTINGS: "/farm-listings",
  FORMULATIONS: "/formulations",
  CLINICAL_TRIALS: "/clinical-trials",
  COMPLIANCE: "/compliance",
  SUBSCRIPTIONS: "/subscriptions",
} as const;
