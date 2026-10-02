export type ChronicCondition = "diabetes" | "hypertension" | "asthma";

export const CONDITIONS: { value: ChronicCondition; label: string }[] = [
  { value: "diabetes", label: "Diabetes" },
  { value: "hypertension", label: "High blood pressure" },
  { value: "asthma", label: "Asthma" }
];

export const DRUG_SOURCES = [
  { value: "pharmacy", label: "Community pharmacy" },
  { value: "hospital", label: "Hospital" },
  { value: "black_market", label: "Informal / open market" },
  { value: "none", label: "I am not taking medicines now" }
] as const;

export const BUDGETS = [
  { value: 500000, label: "₦5,000" },
  { value: 1000000, label: "₦10,000" },
  { value: 2000000, label: "₦20,000" },
  { value: 5000000, label: "₦50,000+" }
] as const;

export function normalizeNigerianPhone(input: string): string {
  const digits = input.replace(/\D/g, "");
  if (digits.startsWith("234") && digits.length === 13) return "+" + digits;
  if (digits.startsWith("0") && digits.length === 11) return "+234" + digits.slice(1);
  if (digits.length === 10) return "+234" + digits;
  throw new Error("Enter a valid Nigerian phone number");
}

export function formatNairaFromKobo(kobo: number): string {
  return new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    maximumFractionDigits: 0
  }).format(kobo / 100);
}
