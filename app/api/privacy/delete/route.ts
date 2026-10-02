import { NextResponse } from "next/server";
import { z } from "zod";
import { requireUser } from "@/lib/auth";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { captureError, trackServerEvent } from "@/lib/telemetry";

const schema = z.object({ confirmation: z.literal("DELETE") });

export async function DELETE(request: Request) {
  const { user } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    schema.parse(await request.json());
    await trackServerEvent(user.id, "privacy_deletion_requested", "users", user.id);
    const admin = createAdminSupabase();
    const { error } = await admin.auth.admin.deleteUser(user.id);
    if (error) throw error;
    return NextResponse.json({ deleted: true });
  } catch (error) {
    captureError(error, { route: "privacy/delete", userId: user.id });
    return NextResponse.json({ error: "Account deletion failed." }, { status: 400 });
  }
}
