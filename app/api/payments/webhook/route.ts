import { NextResponse } from "next/server";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { verifyPaystackSignature } from "@/lib/paystack";
import { captureError, trackServerEvent } from "@/lib/telemetry";

export async function POST(request: Request) {
  const secret = process.env.PAYSTACK_SECRET_KEY;
  if (!secret) return NextResponse.json({ error: "Payment service unavailable." }, { status: 503 });

  const raw = await request.text();
  const signature = request.headers.get("x-paystack-signature") || "";
  if (!verifyPaystackSignature(raw, signature, secret)) {
    return NextResponse.json({ error: "Invalid signature." }, { status: 401 });
  }

  try {
    const event = JSON.parse(raw);
    if (event.event !== "charge.success") return NextResponse.json({ received: true });

    const reference = event.data?.reference;
    const amountKobo = Number(event.data?.amount || 0);
    const rawMetadata = event.data?.metadata || {};
    const metadata = typeof rawMetadata === "string" ? JSON.parse(rawMetadata || "{}") : rawMetadata;
    const userId = metadata.user_id;
    const planId = metadata.plan_id;

    if (!reference || !userId || !planId) {
      return NextResponse.json({ received: true });
    }

    const admin = createAdminSupabase();
    const { data: payment } = await admin
      .from("payments")
      .select("id,status,amount_kobo")
      .eq("ref", reference)
      .maybeSingle();

    if (!payment) return NextResponse.json({ received: true });
    if (payment.status === "success") return NextResponse.json({ received: true });
    if (Number(payment.amount_kobo) !== amountKobo) {
      await admin.from("payments").update({ status: "amount_mismatch" }).eq("id", payment.id);
      return NextResponse.json({ received: true });
    }

    await admin.from("payments").update({
      status: "success",
      provider_payload: event.data,
      updated_at: new Date().toISOString()
    }).eq("id", payment.id);

    const nextBilling = new Date();
    nextBilling.setUTCMonth(nextBilling.getUTCMonth() + 1);

    await admin.from("subscriptions").upsert({
      user_id: userId,
      plan_id: planId,
      status: "active",
      next_billing: nextBilling.toISOString(),
      amount_kobo: amountKobo
    }, { onConflict: "user_id,plan_id" });

    await trackServerEvent(userId, "payment_succeeded", "payments", payment.id, { reference, amountKobo });
    return NextResponse.json({ received: true });
  } catch (error) {
    captureError(error, { route: "payments/webhook" });
    return NextResponse.json({ error: "Webhook processing failed." }, { status: 500 });
  }
}
