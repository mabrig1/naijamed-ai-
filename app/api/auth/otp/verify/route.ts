import { NextResponse } from "next/server";
import { z } from "zod";
import { createServerSupabase } from "@/lib/supabase/server";
import { normalizeNigerianPhone } from "@shared/medinaija-core";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  phone: z.string().min(10).max(24),
  token: z.string().regex(/^\d{6}$/)
});

export async function POST(request: Request) {
  try {
    const parsed = schema.parse(await request.json());
    const phone = normalizeNigerianPhone(parsed.phone);
    const supabase = createServerSupabase();

    const { data, error } = await supabase.auth.verifyOtp({
      phone,
      token: parsed.token,
      type: "sms"
    });

    if (error || !data.user) {
      return NextResponse.json({ error: "That code is invalid or expired." }, { status: 401 });
    }

    const { data: profile } = await supabase
      .from("users")
      .select("monthly_budget_kobo,current_drug_source")
      .eq("id", data.user.id)
      .maybeSingle();

    const onboarded = Boolean(profile?.monthly_budget_kobo && profile?.current_drug_source);
    await trackServerEvent(data.user.id, "auth_otp_verified", "auth");

    return NextResponse.json({ ok: true, onboarded });
  } catch (error) {
    captureError(error, { route: "auth/otp/verify" });
    return NextResponse.json({ error: "Unable to verify OTP." }, { status: 400 });
  }
}
