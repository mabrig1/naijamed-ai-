import { NextResponse } from "next/server";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { sendTermiiSms } from "@/lib/termii";
import { captureError } from "@/lib/telemetry";

export async function GET(request: Request) {
  const expected = process.env.CRON_SECRET;
  const provided = request.headers.get("authorization");
  if (!expected || provided !== "Bearer " + expected) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  const target = new Date();
  target.setUTCDate(target.getUTCDate() + 3);
  const day = target.toISOString().slice(0, 10);

  try {
    const admin = createAdminSupabase();
    const { data, error } = await admin
      .from("medications")
      .select("id,name,refill_date,user_id,users(phone,sms_consent_at)")
      .eq("refill_date", day);

    if (error) throw error;

    let sent = 0;
    for (const medication of data || []) {
      const userRecord = Array.isArray(medication.users) ? medication.users[0] : medication.users;
      const phone = userRecord?.phone;
      if (!phone || !userRecord?.sms_consent_at) continue;

      try {
        await sendTermiiSms(
          phone,
          "MediNaija reminder: your " + medication.name + " refill is due in 3 days. Open MediNaija or use your USSD/SMS refill option. If your prescription has changed, confirm with your doctor/pharmacist first."
        );
        sent += 1;
      } catch (error) {
        captureError(error, { medicationId: medication.id, userId: medication.user_id });
      }
    }

    return NextResponse.json({ ok: true, due: data?.length || 0, sent });
  } catch (error) {
    captureError(error, { route: "cron/refills" });
    return NextResponse.json({ error: "Refill job failed." }, { status: 500 });
  }
}
