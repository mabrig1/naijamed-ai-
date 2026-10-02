"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { cacheGet, cacheSet } from "@/lib/offline";
import { formatNairaFromKobo } from "@shared/medinaija-core";

type Dashboard = {
  nextRefillDate: string | null;
  adherenceStreak: number;
  monthlySpendKobo: number;
  profileComplete: boolean;
  activePlan: string | null;
};

export function DashboardClient() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await fetch("/api/dashboard", { cache: "no-store" });
        if (!response.ok) throw new Error("dashboard");
        const fresh = await response.json();
        if (!active) return;
        setData(fresh);
        setOffline(false);
        await cacheSet("dashboard", fresh);
      } catch {
        const cached = await cacheGet<Dashboard>("dashboard");
        if (!active) return;
        setData(cached);
        setOffline(true);
      }
    }

    load();
    return () => { active = false; };
  }, []);

  async function logAdherence(taken: boolean) {
    await fetch("/api/adherence/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ taken })
    });
    const response = await fetch("/api/dashboard", { cache: "no-store" });
    if (response.ok) {
      const fresh = await response.json();
      setData(fresh);
      await cacheSet("dashboard", fresh);
    }
  }

  if (!data) {
    return <div className="mt-10 rounded-2xl bg-white p-6 text-sm text-slate-500">Loading your care summary…</div>;
  }

  return (
    <div className="pb-24">
      {offline ? <p className="mt-4 rounded-xl bg-amber/20 p-3 text-sm text-green-900">Offline mode: showing your last saved summary.</p> : null}

      <section className="mt-8">
        <p className="text-sm font-semibold text-green-700">Today</p>
        <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">Your care, in one place.</h1>
      </section>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Card>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Next refill</p>
          <CardTitle className="mt-2">{data.nextRefillDate ? new Date(data.nextRefillDate).toLocaleDateString("en-NG") : "Not set"}</CardTitle>
        </Card>
        <Card>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Adherence streak</p>
          <CardTitle className="mt-2">{data.adherenceStreak} days</CardTitle>
        </Card>
        <Card>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">This month</p>
          <CardTitle className="mt-2">{formatNairaFromKobo(data.monthlySpendKobo)}</CardTitle>
        </Card>
      </div>

      <Card className="mt-5">
        <CardTitle>Did you take your medicines today?</CardTitle>
        <p className="mt-2 text-sm text-slate-600">One tap. No long forms.</p>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <Button onClick={() => logAdherence(true)}>Yes, I did</Button>
          <Button variant="outline" onClick={() => logAdherence(false)}>Not yet</Button>
        </div>
      </Card>

      <Card className="mt-5">
        <CardTitle>{data.activePlan || "No active care plan"}</CardTitle>
        <p className="mt-2 text-sm text-slate-600">Need a simpler monthly refill plan?</p>
        <Button asChild className="mt-4 w-full sm:w-auto"><Link href="/plans">View care plans</Link></Button>
      </Card>

      {!data.profileComplete ? (
        <Card className="mt-5 border-amber">
          <CardTitle>Complete your profile</CardTitle>
          <p className="mt-2 text-sm text-slate-600">Add your name, age, state, LGA and next-of-kin so partner pharmacies can support you safely.</p>
          <Button asChild variant="outline" className="mt-4"><Link href="/profile">Complete profile</Link></Button>
        </Card>
      ) : null}

      <p className="mt-6 text-xs leading-5 text-slate-500">
        No smartphone? Refill and status flows are mirrored through SMS/USSD integration. Emergency symptoms should not wait for the app.
      </p>
    </div>
  );
}
