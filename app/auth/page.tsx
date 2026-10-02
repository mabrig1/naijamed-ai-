"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

export default function AuthPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [stage, setStage] = useState<"phone" | "otp">("phone");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submitPhone(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/auth/otp/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Could not send OTP");
      setPhone(body.phone);
      setStage("otp");
      setMessage("We sent a 6-digit code to " + body.phone);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not send OTP");
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch("/api/auth/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, token: otp })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Invalid code");
      router.replace(body.onboarded ? "/dashboard" : "/onboarding");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-md px-5 py-8">
      <Brand />
      <Card className="mt-10">
        <p className="text-sm font-semibold text-green-700">Phone-first sign in</p>
        <h1 className="mt-2 font-serif text-3xl font-semibold text-green-900">
          {stage === "phone" ? "What number should we reach you on?" : "Enter your OTP"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          {stage === "phone"
            ? "Use a Nigerian mobile number. Email is optional."
            : "The code expires quickly. Never share it with an agent or pharmacy."}
        </p>

        {stage === "phone" ? (
          <form className="mt-6" onSubmit={submitPhone}>
            <label className="text-sm font-semibold text-green-900">Phone number</label>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="0803 123 4567"
              inputMode="tel"
              className="mt-2 h-12 w-full rounded-xl border bg-white px-4 outline-none focus:ring-2 focus:ring-green-600"
              required
            />
            <Button className="mt-4 w-full" disabled={busy}>{busy ? "Sending..." : "Send OTP"}</Button>
          </form>
        ) : (
          <form className="mt-6" onSubmit={verify}>
            <label className="text-sm font-semibold text-green-900">6-digit code</label>
            <input
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="123456"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="mt-2 h-12 w-full rounded-xl border bg-white px-4 text-center text-xl tracking-[0.3em] outline-none focus:ring-2 focus:ring-green-600"
              required
            />
            <Button className="mt-4 w-full" disabled={busy || otp.length < 6}>{busy ? "Checking..." : "Continue"}</Button>
            <button type="button" onClick={() => setStage("phone")} className="mt-4 w-full text-sm font-semibold text-green-700">Use another number</button>
          </form>
        )}

        {message ? <p className="mt-4 rounded-xl bg-green-50 p-3 text-sm text-green-900">{message}</p> : null}
      </Card>
    </main>
  );
}
