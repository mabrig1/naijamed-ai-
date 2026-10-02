import Link from "next/link";
import { redirect } from "next/navigation";
import { Brand } from "@/components/brand";
import { DashboardClient } from "@/components/dashboard-client";
import { LanguageSwitcher } from "@/components/language-switcher";
import { requireUser } from "@/lib/auth";

export default async function DashboardPage() {
  const { user } = await requireUser();
  if (!user) redirect("/auth");

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-5 py-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Brand />
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <Link href="/profile" className="text-sm font-semibold text-green-700">Profile</Link>
        </div>
      </div>
      <DashboardClient />
    </main>
  );
}
