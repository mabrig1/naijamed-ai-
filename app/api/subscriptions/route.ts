import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { trackServerEvent } from "@/lib/telemetry";

const schema = z.object({ planId: z.string().uuid() });

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  const body = schema.parse(await request.json());
  const { data: plan, error: planError } = await supabase
    .from("plans")
    .select("id,monthly_price_kobo")
    .eq("id", body.planId)
    .eq("active", true)
    .single();

  if (planError || !plan) return NextResponse.json({ error: "Plan not found." }, { status: 404 });

  const nextBilling = new Date();
  nextBilling.setUTCMonth(nextBilling.getUTCMonth() + 1);

  const { data, error } = await supabase.from("subscriptions").insert({
    user_id: user.id,
    plan_id: plan.id,
    status: "pending_payment",
    next_billing: nextBilling.toISOString(),
    amount_kobo: plan.monthly_price_kobo
  }).select("id").single();

  if (error) return NextResponse.json({ error: "Could not create subscription." }, { status: 400 });
  await trackServerEvent(user.id, "subscription_created", "subscriptions", data.id);
  return NextResponse.json({ id: data.id, status: "pending_payment" }, { status: 201 });
}
