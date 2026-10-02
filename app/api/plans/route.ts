import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

export async function GET() {
  const supabase = createServerSupabase();
  const { data, error } = await supabase
    .from("plans")
    .select("id,slug,name,conditions,monthly_price_kobo,drugs,price_valid_until")
    .eq("active", true)
    .order("monthly_price_kobo");

  if (error) return NextResponse.json({ error: "Plans unavailable." }, { status: 500 });
  return NextResponse.json(data, { headers: { "Cache-Control": "public, max-age=300" } });
}
