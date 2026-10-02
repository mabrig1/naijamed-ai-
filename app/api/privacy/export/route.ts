import { NextResponse } from "next/server";
import { requireUser } from "@/lib/auth";
import { captureError, trackServerEvent } from "@/lib/telemetry";

export async function GET() {
  const { user, supabase } = await requireUser();
  if (!user) return NextResponse.json({ error: "Sign in required." }, { status: 401 });

  try {
    const tables = [
      "users",
      "conditions",
      "subscriptions",
      "medications",
      "adherence_logs",
      "orders",
      "payments",
      "triage_sessions",
      "audit_logs"
    ] as const;

    const result: Record<string, unknown> = {
      exported_at: new Date().toISOString(),
      auth_user_id: user.id
    };

    for (const table of tables) {
      const query = supabase.from(table).select("*");
      const response = table === "users"
        ? await query.eq("id", user.id)
        : table === "audit_logs"
          ? await query.eq("actor_id", user.id)
          : await query.eq("user_id", user.id);
      result[table] = response.data || [];
    }

    await trackServerEvent(user.id, "privacy_export_requested", "users", user.id);
    return new NextResponse(JSON.stringify(result, null, 2), {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": "attachment; filename=medinaija-data-export.json",
        "Cache-Control": "no-store"
      }
    });
  } catch (error) {
    captureError(error, { route: "privacy/export", userId: user.id });
    return NextResponse.json({ error: "Could not prepare export." }, { status: 500 });
  }
}
