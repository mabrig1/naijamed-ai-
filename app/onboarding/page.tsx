"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { BUDGETS, CONDITIONS, DRUG_SOURCES, type ChronicCondition } from "@shared/medinaija-core";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [conditions, setConditions] = useState<ChronicCondition[]>([]);
  const [drugSource, setDrugSource] = useState("");
  const [budgetKobo, setBudgetKobo] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const canContinue = useMemo(() => {
    if (step === 1) return conditions.length > 0;
    if (step === 2) return Boolean(drugSource);
    return Boolean(budgetKobo);
  }, [step, conditions, drugSource, budgetKobo]);

  function toggleCondition(value: ChronicCondition) {
    setConditions((current) =>
      current.includes(value) ? current.filter((item) => item !== value) : [...current, value]
    );
  }

  async function finish() {
    setBusy(true);
    setError("");
    try {
      const consentAt = localStorage.getItem("medinaija_consent_health");
      const smsConsentAt = localStorage.getItem("medinaija_consent_sms");
      const response = await fetch("/api/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conditions, drugSource, budgetKobo, consentAt, smsConsentAt })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Could not save your answers");
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save your answers");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-xl px-5 py-8">
      <Brand />
      <div className="mt-8 flex gap-2" aria-label={"Step " + step + " of 3"}>
        {[1, 2, 3].map((item) => (
          <span key={item} className={"h-2 flex-1 rounded-full " + (item <= step ? "bg-green-600" : "bg-green-900/10")} />
        ))}
      </div>

      <Card className="mt-5">
        {step === 1 ? (
          <>
            <p className="text-sm font-semibold text-green-700">Step 1 of 3</p>
            <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">What condition(s) do you manage?</h1>
            <div className="mt-6 grid gap-3">
              {CONDITIONS.map((item) => (
                <button
                  key={item.value}
                  onClick={() => toggleCondition(item.value)}
                  className={"min-h-14 rounded-xl border p-4 text-left font-semibold " +
                    (conditions.includes(item.value) ? "border-green-600 bg-green-50 text-green-900" : "bg-white text-slate-700")}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </>
        ) : null}

        {step === 2 ? (
          <>
            <p className="text-sm font-semibold text-green-700">Step 2 of 3</p>
            <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">How do you currently get your drugs?</h1>
            <div className="mt-6 grid gap-3">
              {DRUG_SOURCES.map((item) => (
                <button
                  key={item.value}
                  onClick={() => setDrugSource(item.value)}
                  className={"min-h-14 rounded-xl border p-4 text-left font-semibold " +
                    (drugSource === item.value ? "border-green-600 bg-green-50 text-green-900" : "bg-white text-slate-700")}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </>
        ) : null}

        {step === 3 ? (
          <>
            <p className="text-sm font-semibold text-green-700">Step 3 of 3</p>
            <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">Monthly budget for medicines?</h1>
            <p className="mt-3 text-sm text-slate-600">This helps us show realistic options. It does not change your medical care.</p>
            <div className="mt-6 grid grid-cols-2 gap-3">
              {BUDGETS.map((item) => (
                <button
                  key={item.value}
                  onClick={() => setBudgetKobo(item.value)}
                  className={"min-h-14 rounded-xl border p-4 text-center font-semibold " +
                    (budgetKobo === item.value ? "border-green-600 bg-green-50 text-green-900" : "bg-white text-slate-700")}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </>
        ) : null}

        {error ? <p className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}

        <div className="mt-7 flex gap-3">
          {step > 1 ? <Button variant="outline" onClick={() => setStep((s) => s - 1)}>Back</Button> : null}
          <Button
            className="flex-1"
            disabled={!canContinue || busy}
            onClick={() => step < 3 ? setStep((s) => s + 1) : finish()}
          >
            {step < 3 ? "Continue" : busy ? "Saving..." : "Finish setup"}
          </Button>
        </div>
      </Card>
    </main>
  );
}
