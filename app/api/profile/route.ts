import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({
  name: z.string().trim().min(2).max(120),
  dob: z.string().optional(),
  state: z.string().trim().min(2).max(80),
  lga: z.string().trim().min(2).max(100),
  email: z.string().email().or(z.literal("")).optional(),
  nextOfKinName: z.string().trim().max(120).optional(),
  nextOfKinPhone: z.string().trim().max(24).optional()
});

export async function GET() {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  const { data, error } = await supabase.from("users").select("*").eq("id", user.id).single();
  if (error) return NextResponse.json({ error: "Profile unavailable." }, { status: 500 });
  return NextResponse.json(data);
}

export async function PUT(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const body = schema.parse(await request.json());
    const { error } = await supabase.from("users").upsert({
      id: user.id,
      phone: user.phone,
      name: body.name,
      dob: body.dob || null,
      state: body.state,
      lga: body.lga,
      email: body.email || null,
      next_of_kin: {
        name: body.nextOfKinName || "",
        phone: body.nextOfKinPhone || ""
      }
    });
    if (error) throw error;

    await trackServerEvent(user.id, "profile_updated", "users", user.id);
    return NextResponse.json({ ok: true });
  } catch (error) {
    captureError(error, { route: "profile", userId: user.id });
    return NextResponse.json({ error: "Could not save profile." }, { status: 400 });
  }
}
