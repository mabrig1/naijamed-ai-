import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { trackServerEvent } from "@/lib/telemetry";

const schema = z.object({ language: z.enum(["en", "yo", "ha", "ig", "pcm"]) });

export async function POST(request: Request) {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  const body = schema.parse(await request.json());
  const { error } = await supabase.from("users").update({ preferred_language: body.language }).eq("id", user.id);
  if (error) return NextResponse.json({ error: "Could not save language." }, { status: 400 });

  await trackServerEvent(user.id, "language_changed", "users", user.id, { language: body.language });
  return NextResponse.json({ ok: true });
}
