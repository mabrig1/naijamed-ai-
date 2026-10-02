import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  conditions: z.array(z.enum(["diabetes", "hypertension", "asthma"])).min(1),
  drugSource: z.enum(["pharmacy", "hospital", "black_market", "none"]),
  budgetKobo: z.number().int().positive(),
  consentAt: z.string().datetime().nullable().optional(),
  smsConsentAt: z.string().datetime().nullable().optional()
});

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const body = schema.parse(await request.json());

    const { error: profileError } = await supabase.from("users").upsert({
      id: user.id,
      phone: user.phone,
      email: user.email,
      current_drug_source: body.drugSource,
      monthly_budget_kobo: body.budgetKobo,
      consent_at: body.consentAt || new Date().toISOString(),
      sms_consent_at: body.smsConsentAt || null
    });

    if (profileError) throw profileError;

    const { error: deleteError } = await supabase.from("conditions").delete().eq("user_id", user.id);
    if (deleteError) throw deleteError;

    const { error: conditionsError } = await supabase.from("conditions").insert(
      body.conditions.map((type) => ({ user_id: user.id, type }))
    );
    if (conditionsError) throw conditionsError;

    await trackServerEvent(user.id, "onboarding_completed", "users", user.id, {
      conditions: body.conditions,
      drugSource: body.drugSource,
      budgetBandKobo: body.budgetKobo
    });

    return NextResponse.json({ ok: true });
  } catch (error) {
    captureError(error, { route: "onboarding", userId: user.id });
    return NextResponse.json({ error: "Could not save onboarding. Please retry." }, { status: 400 });
  }
}
