import Link from "next/link";
import { ArrowRight, BellRing, MapPin, ShieldCheck, Smartphone } from "lucide-react";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: BellRing,
    title: "Never miss a refill",
    text: "Simple medicine check-ins plus SMS reminders when you have not opened the app."
  },
  {
    icon: MapPin,
    title: "Verified pharmacy access",
    text: "Find partner pharmacies nearby for pickup, with delivery support where available."
  },
  {
    icon: Smartphone,
    title: "Built for real Nigerian networks",
    text: "Low-bandwidth screens, offline cache and SMS/USSD fallback for critical actions."
  },
  {
    icon: ShieldCheck,
    title: "Your health data stays protected",
    text: "Consent-first access, row-level security, audit logs and deletion/export pathways."
  }
];

export default function HomePage() {
  return (
    <main className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Brand />
        <Link href="/auth" className="text-sm font-semibold text-green-700">Sign in</Link>
      </header>

      <section className="mx-auto grid max-w-6xl gap-10 px-5 pb-14 pt-10 md:grid-cols-[1.15fr_.85fr] md:items-center md:py-20">
        <div>
          <div className="mb-5 inline-flex rounded-full bg-green-50 px-4 py-2 text-sm font-semibold text-green-700">
            🇳🇬 Chronic care built around Nigerian realities
          </div>
          <h1 className="max-w-3xl font-serif text-4xl font-semibold leading-tight text-green-900 sm:text-5xl md:text-6xl">
            Your chronic care companion — drugs, delivery, and check-ins in one plan.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg">
            Keep your diabetes, high blood pressure or asthma care organised without complicated hospital queues.
            MediNaija helps you plan refills, track adherence and reach verified care partners.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button asChild>
              <Link href="/consent">Start with your phone <ArrowRight className="ml-2 h-4 w-4" /></Link>
            </Button>
            <Button asChild variant="outline">
              <Link href="/plans">See plans in ₦</Link>
            </Button>
          </div>
          <p className="mt-4 text-xs leading-5 text-slate-500">
            Medicine supply is subject to a valid prescription where required and pharmacist/doctor review. MediNaija does not replace your doctor.
          </p>
        </div>

        <Card className="bg-green-900 text-white">
          <p className="text-sm font-semibold text-amber">This month at a glance</p>
          <div className="mt-5 space-y-4">
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs text-green-50">Next refill</p>
              <p className="mt-1 font-serif text-2xl">3 days</p>
            </div>
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs text-green-50">Adherence streak</p>
              <p className="mt-1 font-serif text-2xl">12 days</p>
            </div>
            <div className="rounded-xl bg-white/10 p-4">
              <p className="text-xs text-green-50">Plan</p>
              <p className="mt-1 text-lg font-semibold">Hypertension Plus · ₦5,000/mo</p>
            </div>
          </div>
        </Card>
      </section>

      <section className="border-y border-green-900/10 bg-white/55">
        <div className="mx-auto grid max-w-6xl gap-4 px-5 py-12 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, text }) => (
            <Card key={title} className="shadow-none">
              <Icon className="h-6 w-6 text-green-600" />
              <CardTitle className="mt-4 text-lg">{title}</CardTitle>
              <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
            </Card>
          ))}
        </div>
      </section>

      <footer className="mx-auto max-w-6xl px-5 py-10 text-sm text-slate-500">
        <p className="font-semibold text-green-900">MediNaija</p>
        <p className="mt-1">A chronic-care product by MABRIG Technologies.</p>
      </footer>
    </main>
  );
}
