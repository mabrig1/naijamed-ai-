import * as Sentry from "@sentry/nextjs";
import { createAdminSupabase } from "@/lib/supabase/admin";

export async function trackServerEvent(
  actorId: string | null,
  action: string,
  entity: string,
  entityId?: string | null,
  metadata?: Record<string, unknown>
) {
  try {
    const admin = createAdminSupabase();
    await admin.from("audit_logs").insert({
      actor_id: actorId,
      action,
      entity,
      entity_id: entityId ?? null,
      metadata: metadata ?? {},
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    Sentry.captureException(error);
  }
}

export function captureError(error: unknown, context?: Record<string, unknown>) {
  Sentry.captureException(error, { extra: context });
}
