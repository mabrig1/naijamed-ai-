"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

declare global {
  interface Window {
    PaystackPop?: new () => { resumeTransaction: (accessCode: string) => void };
  }
}

function loadPaystackInline() {
  return new Promise<void>((resolve, reject) => {
    if (window.PaystackPop) return resolve();
    const existing = document.querySelector<HTMLScriptElement>('script[data-medinaija-paystack="true"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Could not load Paystack")), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.src = "https://js.paystack.co/v2/inline.js";
    script.async = true;
    script.dataset.medinaijaPaystack = "true";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Paystack"));
    document.head.appendChild(script);
  });
}

export function SubscribeButton({ planSlug }: { planSlug: string }) {
  const [busy, setBusy] = useState<"card" | "ussd" | null>(null);
  const [error, setError] = useState("");

  async function pay(channel: "card" | "ussd") {
    setBusy(channel);
    setError("");
    try {
      const response = await fetch("/api/payments/initiate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ planSlug, channel })
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Could not start payment");

      await loadPaystackInline();
      if (!window.PaystackPop) {
        window.location.href = body.authorizationUrl;
        return;
      }

      const popup = new window.PaystackPop();
      popup.resumeTransaction(body.accessCode);
      setBusy(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start payment");
      setBusy(null);
    }
  }

  return (
    <div className="mt-5 space-y-2">
      <Button className="w-full" onClick={() => pay("card")} disabled={Boolean(busy)}>
        {busy === "card" ? "Opening checkout..." : "Subscribe"}
      </Button>
      <Button variant="outline" className="w-full" onClick={() => pay("ussd")} disabled={Boolean(busy)}>
        {busy === "ussd" ? "Opening USSD options..." : "Pay with USSD"}
      </Button>
      {error ? <p className="text-xs text-red-700">{error}</p> : null}
    </div>
  );
}
