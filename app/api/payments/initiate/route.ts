import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { initializePaystack } from "@/lib/paystack";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  planSlug: z.string().min(2).max(80),
  channel: z.enum(["card", "ussd"]).default("card")
});

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const body = schema.parse(await request.json());
    const { data: plan, error: planError } = await supabase
      .from("plans")
      .select("id,slug,name,monthly_price_kobo,active")
      .eq("slug", body.planSlug)
      .eq("active", true)
      .single();

    if (planError || !plan) return NextResponse.json({ error: "Plan not found." }, { status: 404 });

    const { data: profile } = await supabase.from("users").select("phone,email").eq("id", user.id).single();
    const phoneDigits = String(profile?.phone || user.phone || user.id).replace(/\D/g, "");
    const paymentEmail = profile?.email || user.email || (phoneDigits + "@pay.medinaija.ng");
    const appUrl = process.env.NEXT_PUBLIC_APP_URL || new URL(request.url).origin;

    const checkout = await initializePaystack({
      email: paymentEmail,
      amountKobo: plan.monthly_price_kobo,
      channels: body.channel === "ussd" ? ["ussd"] : ["card", "bank", "bank_transfer"],
      callbackUrl: appUrl + "/dashboard?payment=return",
      metadata: {
        user_id: user.id,
        plan_id: plan.id,
        plan_slug: plan.slug,
        source: "medinaija"
      }
    });

    const { error: paymentError } = await supabase.from("payments").insert({
      user_id: user.id,
      provider: "paystack",
      ref: checkout.reference,
      status: "pending",
      amount_kobo: plan.monthly_price_kobo,
      metadata: { plan_id: plan.id, plan_slug: plan.slug, channel: body.channel }
    });
    if (paymentError) throw paymentError;

    await trackServerEvent(user.id, "payment_initiated", "payments", checkout.reference, {
      planSlug: plan.slug,
      channel: body.channel,
      amountKobo: plan.monthly_price_kobo
    });

    return NextResponse.json({
      authorizationUrl: checkout.authorization_url,
      accessCode: checkout.access_code,
      reference: checkout.reference
    });
  } catch (error) {
    captureError(error, { route: "payments/initiate", userId: user.id });
    return NextResponse.json({ error: "Could not start payment." }, { status: 400 });
  }
}
