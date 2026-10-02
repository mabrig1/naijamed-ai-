import Link from "next/link";
import { Brand } from "@/components/brand";
import { Card, CardTitle } from "@/components/ui/card";
import { SubscribeButton } from "@/components/subscribe-button";

const plans = [
  {
    slug: "diabetes-basic",
    name: "Diabetes Basic",
    price: "₦2,000/mo",
    drugs: "Metformin support bundle",
    note: "Includes refill and BP-check reminders."
  },
  {
    slug: "hypertension-plus",
    name: "Hypertension Plus",
    price: "₦5,000/mo",
    drugs: "Amlodipine + Lisinopril support bundle",
    note: "Includes remote BP logging."
  },
  {
    slug: "diabetes-htn-combo",
    name: "Diabetes + HTN Combo",
    price: "₦8,000/mo",
    drugs: "Combined chronic-care refill support",
    note: "Built for people managing both conditions."
  }
];

export default function PlansPage() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-5 py-6">
      <div className="flex items-center justify-between gap-4">
        <Brand />
        <Link href="/dashboard" className="text-sm font-semibold text-green-700">Dashboard</Link>
      </div>

      <section className="mt-10 max-w-2xl">
        <p className="text-sm font-semibold text-green-700">Monthly care plans</p>
        <h1 className="mt-2 font-serif text-4xl font-semibold text-green-900">Know what you are paying for.</h1>
        <p className="mt-4 text-sm leading-6 text-slate-600">
          Prices are locked monthly and shown in Naira. Drug fulfilment is subject to prescription validation where required and pharmacist/doctor review.
        </p>
      </section>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.slug} className="flex flex-col">
            <p className="text-sm font-semibold text-green-700">{plan.price}</p>
            <CardTitle className="mt-2">{plan.name}</CardTitle>
            <p className="mt-4 text-sm font-semibold text-slate-700">{plan.drugs}</p>
            <p className="mt-2 flex-1 text-sm leading-6 text-slate-500">{plan.note}</p>
            <SubscribeButton planSlug={plan.slug} />
          </Card>
        ))}
      </div>

      <Card className="mt-6">
        <CardTitle>Need a custom plan?</CardTitle>
        <p className="mt-2 text-sm text-slate-600">
          A custom plan builder is part of the core loop; final drug selection still requires clinical/pharmacy validation.
        </p>
        <Link href="/profile" className="mt-4 inline-block text-sm font-semibold text-green-700">Update your medicines and budget →</Link>
      </Card>

      <p className="mt-6 text-xs leading-5 text-slate-500">
        Paystack card and USSD checkout are supported. The USSD menu for refill/status requires an aggregator shortcode before production activation.
      </p>
    </main>
  );
}
