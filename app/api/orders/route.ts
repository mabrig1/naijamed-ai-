import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  pharmacyId: z.string().uuid(),
  planId: z.string().uuid(),
  deliveryType: z.enum(["pickup", "delivery"])
});

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const body = schema.parse(await request.json());

    const [{ data: plan }, { data: pharmacy }] = await Promise.all([
      supabase.from("plans").select("id,monthly_price_kobo").eq("id", body.planId).eq("active", true).single(),
      supabase.from("pharmacies").select("id,pcn_license").eq("id", body.pharmacyId).single()
    ]);

    if (!plan || !pharmacy) return NextResponse.json({ error: "Plan or pharmacy not found." }, { status: 404 });

    const { data, error } = await supabase.from("orders").insert({
      user_id: user.id,
      pharmacy_id: pharmacy.id,
      status: "pending",
      delivery_type: body.deliveryType,
      total_kobo: plan.monthly_price_kobo,
      metadata: {
        plan_id: plan.id,
        delivery_partner: body.deliveryType === "delivery" ? "pending_dispatch_partner" : null
      }
    }).select("id").single();

    if (error) throw error;
    await trackServerEvent(user.id, "order_created", "orders", data.id, { deliveryType: body.deliveryType });
    return NextResponse.json({ id: data.id, status: "pending" }, { status: 201 });
  } catch (error) {
    captureError(error, { route: "orders", userId: user.id });
    return NextResponse.json({ error: "Could not create refill order." }, { status: 400 });
  }
}
