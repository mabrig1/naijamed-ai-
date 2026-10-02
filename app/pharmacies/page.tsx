import Link from "next/link";
import { Brand } from "@/components/brand";
import { PharmacyLocator } from "@/components/pharmacy-locator";

export default function PharmaciesPage() {
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-5 py-6">
      <div className="flex items-center justify-between gap-4">
        <Brand />
        <Link href="/dashboard" className="text-sm font-semibold text-green-700">Dashboard</Link>
      </div>
      <section className="mt-10">
        <p className="text-sm font-semibold text-green-700">Partner pharmacy locator</p>
        <h1 className="mt-2 font-serif text-4xl font-semibold text-green-900">Find a pharmacy within 5km.</h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
          We show PCN licence details in the partner record. Demo seed pharmacies are clearly marked until live partners are verified.
        </p>
      </section>
      <PharmacyLocator />
    </main>
  );
}
