"use client";

import { useEffect, useRef, useState } from "react";
import { MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";

type Pharmacy = {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  lat: number;
  lng: number;
  pcn_license: string;
  partner_tier: string;
  distance_km: number;
};

declare global {
  interface Window {
    google?: any;
  }
}

export function PharmacyLocator() {
  const [items, setItems] = useState<Pharmacy[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [showMap, setShowMap] = useState(false);
  const mapHost = useRef<HTMLDivElement>(null);

  function locate() {
    setBusy(true);
    setMessage("");
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const response = await fetch("/api/pharmacies/nearby?lat=" + coords.latitude + "&lng=" + coords.longitude);
          const body = await response.json();
          if (!response.ok) throw new Error(body.error || "Could not load pharmacies");
          setItems(body);
          setMessage(body.length ? "" : "No seeded partner pharmacy is within 5km of this location yet.");
        } catch (error) {
          setMessage(error instanceof Error ? error.message : "Could not load pharmacies");
        } finally {
          setBusy(false);
        }
      },
      () => {
        setBusy(false);
        setMessage("Location permission is needed to search within 5km. You can still ask an agent by SMS/USSD.");
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 600000 }
    );
  }

  useEffect(() => {
    if (!showMap || !items.length || !mapHost.current) return;
    const key = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
    if (!key) {
      setMessage("Google Maps key is not configured yet. The pharmacy list still works.");
      return;
    }

    let cancelled = false;

    function renderMap() {
      if (cancelled || !mapHost.current || !window.google) return;
      const center = { lat: items[0].lat, lng: items[0].lng };
      const map = new window.google.maps.Map(mapHost.current, {
        center,
        zoom: 13,
        disableDefaultUI: true,
        zoomControl: true
      });

      items.forEach((pharmacy) => {
        new window.google.maps.Marker({
          position: { lat: pharmacy.lat, lng: pharmacy.lng },
          map,
          title: pharmacy.name
        });
      });
    }

    if (window.google?.maps) {
      renderMap();
      return () => { cancelled = true; };
    }

    const script = document.createElement("script");
    script.src = "https://maps.googleapis.com/maps/api/js?key=" + encodeURIComponent(key);
    script.async = true;
    script.defer = true;
    script.onload = renderMap;
    script.onerror = () => setMessage("Google Maps could not load on this connection.");
    document.head.appendChild(script);

    return () => { cancelled = true; };
  }, [showMap, items]);

  return (
    <section className="mt-7">
      <div className="flex flex-wrap gap-3">
        <Button onClick={locate} disabled={busy}>
          <MapPin className="mr-2 h-4 w-4" />
          {busy ? "Finding nearby pharmacies..." : "Use my location"}
        </Button>
        {items.length ? (
          <Button variant="outline" onClick={() => setShowMap((value) => !value)}>
            {showMap ? "Hide map" : "Show partner map"}
          </Button>
        ) : null}
      </div>

      {showMap ? <div ref={mapHost} className="mt-5 h-72 w-full overflow-hidden rounded-2xl bg-green-50" /> : null}
      {message ? <p className="mt-4 rounded-xl bg-white p-4 text-sm text-slate-600">{message}</p> : null}

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {items.map((pharmacy) => (
          <Card key={pharmacy.id}>
            <CardTitle>{pharmacy.name}</CardTitle>
            <p className="mt-2 text-sm text-slate-600">{pharmacy.address}</p>
            <p className="mt-3 text-xs font-semibold text-green-700">{pharmacy.distance_km.toFixed(1)} km away</p>
            <p className="mt-1 text-xs text-slate-500">PCN: {pharmacy.pcn_license}</p>
            <a
              className="mt-4 inline-block text-sm font-semibold text-green-700"
              target="_blank"
              rel="noreferrer"
              href={"https://www.google.com/maps/search/?api=1&query=" + pharmacy.lat + "," + pharmacy.lng}
            >
              Open in Google Maps →
            </a>
          </Card>
        ))}
      </div>
    </section>
  );
}
