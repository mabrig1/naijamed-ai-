import crypto from "node:crypto";

export function verifyPaystackSignature(rawBody: string, signature: string, secret: string) {
  const hash = crypto.createHmac("sha512", secret).update(rawBody).digest("hex");
  const a = Buffer.from(hash);
  const b = Buffer.from(signature || "");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

export async function initializePaystack(input: {
  email: string;
  amountKobo: number;
  channels: ("card" | "bank" | "ussd" | "bank_transfer")[];
  metadata: Record<string, unknown>;
  callbackUrl?: string;
}) {
  const secret = process.env.PAYSTACK_SECRET_KEY;
  if (!secret) throw new Error("PAYSTACK_SECRET_KEY is not configured");

  const response = await fetch("https://api.paystack.co/transaction/initialize", {
    method: "POST",
    headers: {
      Authorization: "Bearer " + secret,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      email: input.email,
      amount: String(input.amountKobo),
      currency: "NGN",
      channels: input.channels,
      metadata: JSON.stringify(input.metadata),
      callback_url: input.callbackUrl
    }),
    cache: "no-store"
  });

  const body = await response.json();
  if (!response.ok || !body.status) throw new Error(body.message || "Unable to initialize payment");
  return body.data as { authorization_url: string; access_code: string; reference: string };
}
