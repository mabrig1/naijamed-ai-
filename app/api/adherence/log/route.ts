import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  medicationId: z.string().uuid().nullable().optional(),
  taken: z.boolean()
});

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const body = schema.parse(await request.json());
    const { data, error } = await supabase.from("adherence_logs").insert({
      user_id: user.id,
      medication_id: body.medicationId || null,
      taken_bool: body.taken,
      taken_at: new Date().toISOString(),
      method: "app"
    }).select("id").single();

    if (error) throw error;
    await trackServerEvent(user.id, "adherence_logged", "adherence_logs", data.id, { taken: body.taken });
    return NextResponse.json({ ok: true, id: data.id }, { status: 201 });
  } catch (error) {
    captureError(error, { route: "adherence/log", userId: user.id });
    return NextResponse.json({ error: "Could not save check-in." }, { status: 400 });
  }
}
