"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function ConsentPage() {
  const router = useRouter();
  const [health, setHealth] = useState(false);
  const [sms, setSms] = useState(false);

  function continueFlow() {
    if (!health) return;
    localStorage.setItem("medinaija_consent_health", new Date().toISOString());
    localStorage.setItem("medinaija_consent_sms", sms ? new Date().toISOString() : "");
    router.push("/auth");
  }

  return (
    <main className="mx-auto min-h-screen max-w-xl px-5 py-8">
      <Brand />
      <Card className="mt-10">
        <p className="text-sm font-semibold text-green-700">Before we begin</p>
        <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">You control your health data.</h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          MediNaija uses your health details to organise refills, adherence check-ins and care support.
          We do not sell your health information. You can request an export or deletion from your profile.
        </p>

        <label className="mt-6 flex cursor-pointer gap-3 rounded-xl border p-4">
          <input type="checkbox" checked={health} onChange={(e) => setHealth(e.target.checked)} className="mt-1 h-5 w-5" />
          <span>
            <span className="block font-semibold text-green-900">I consent to processing my health data for chronic-care services.</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Required to use MediNaija care features.</span>
          </span>
        </label>

        <label className="mt-3 flex cursor-pointer gap-3 rounded-xl border p-4">
          <input type="checkbox" checked={sms} onChange={(e) => setSms(e.target.checked)} className="mt-1 h-5 w-5" />
          <span>
            <span className="block font-semibold text-green-900">Send me care reminders by SMS.</span>
            <span className="mt-1 block text-xs leading-5 text-slate-500">Optional. Useful when you are offline or have not opened the app.</span>
          </span>
        </label>

        <Button className="mt-6 w-full" disabled={!health} onClick={continueFlow}>Continue</Button>
      </Card>
    </main>
  );
}
