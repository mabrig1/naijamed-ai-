import { NextResponse } from "next/server";
import { z } from "zod";
import { createServerSupabase } from "@/lib/supabase/server";
import { normalizeNigerianPhone } from "@shared/medinaija-core";
import { captureError } from "@/lib/telemetry";

const schema = z.object({ phone: z.string().min(10).max(24) });

export async function POST(request: Request) {
  try {
    const parsed = schema.parse(await request.json());
    const phone = normalizeNigerianPhone(parsed.phone);
    const supabase = createServerSupabase();
    const { error } = await supabase.auth.signInWithOtp({ phone });
    if (error) return NextResponse.json({ error: "Could not send OTP. Please try again." }, { status: 400 });
    return NextResponse.json({ ok: true, phone });
  } catch (error) {
    captureError(error, { route: "auth/otp/send" });
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Invalid phone number" },
      { status: 400 }
    );
  }
}
