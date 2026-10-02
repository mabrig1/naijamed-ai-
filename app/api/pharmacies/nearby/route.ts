import { NextResponse } from "next/server";
import { createServerSupabase } from "@/lib/supabase/server";

function distanceKm(lat1: number, lng1: number, lat2: number, lng2: number) {
  const toRad = (value: number) => value * Math.PI / 180;
  const earth = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return earth * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const lat = Number(url.searchParams.get("lat"));
  const lng = Number(url.searchParams.get("lng"));
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return NextResponse.json({ error: "lat and lng are required." }, { status: 400 });
  }

  const supabase = createServerSupabase();
  const { data, error } = await supabase
    .from("pharmacies")
    .select("id,name,address,city,state,lat,lng,pcn_license,partner_tier");

  if (error) return NextResponse.json({ error: "Pharmacies unavailable." }, { status: 500 });

  const nearby = (data || [])
    .map((pharmacy) => ({ ...pharmacy, distance_km: distanceKm(lat, lng, pharmacy.lat, pharmacy.lng) }))
    .filter((pharmacy) => pharmacy.distance_km <= 5)
    .sort((a, b) => a.distance_km - b.distance_km)
    .slice(0, 20);

  return NextResponse.json(nearby);
}
