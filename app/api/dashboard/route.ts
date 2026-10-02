import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { captureError } from "@/lib/telemetry";

function adherenceStreak(rows: { taken_at: string; taken_bool: boolean }[]) {
  const takenDays = new Set(
    rows.filter((row) => row.taken_bool).map((row) => new Date(row.taken_at).toISOString().slice(0, 10))
  );
  let streak = 0;
  const cursor = new Date();
  for (let i = 0; i < 30; i += 1) {
    const day = cursor.toISOString().slice(0, 10);
    if (!takenDays.has(day)) break;
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}

export async function GET() {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const monthStart = new Date();
    monthStart.setUTCDate(1);
    monthStart.setUTCHours(0, 0, 0, 0);

    const [profileResult, refillResult, adherenceResult, paymentResult, subscriptionResult] = await Promise.all([
      supabase.from("users").select("name,dob,state,lga").eq("id", user.id).maybeSingle(),
      supabase.from("medications").select("refill_date").eq("user_id", user.id).not("refill_date", "is", null).order("refill_date").limit(1),
      supabase.from("adherence_logs").select("taken_at,taken_bool").eq("user_id", user.id).gte("taken_at", new Date(Date.now() - 30 * 86400000).toISOString()).order("taken_at", { ascending: false }),
      supabase.from("payments").select("amount_kobo").eq("user_id", user.id).eq("status", "success").gte("created_at", monthStart.toISOString()),
      supabase.from("subscriptions").select("plans(name)").eq("user_id", user.id).eq("status", "active").order("created_at", { ascending: false }).limit(1)
    ]);

    const monthlySpendKobo = (paymentResult.data || []).reduce((sum, row) => sum + Number(row.amount_kobo || 0), 0);
    const profile = profileResult.data;
    const subscription = subscriptionResult.data?.[0] as { plans?: { name?: string } | null } | undefined;

    return NextResponse.json({
      nextRefillDate: refillResult.data?.[0]?.refill_date || null,
      adherenceStreak: adherenceStreak(adherenceResult.data || []),
      monthlySpendKobo,
      profileComplete: Boolean(profile?.name && profile?.dob && profile?.state && profile?.lga),
      activePlan: subscription?.plans?.name || null
    });
  } catch (error) {
    captureError(error, { route: "dashboard", userId: user.id });
    return NextResponse.json({ error: "Dashboard unavailable." }, { status: 500 });
  }
}
