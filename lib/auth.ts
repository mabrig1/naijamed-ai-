import { createServerSupabase } from "@/lib/supabase/server";

export async function requireUser() {
  const supabase = createServerSupabase();
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error || !user) return { user: null, supabase };
  return { user, supabase };
}
