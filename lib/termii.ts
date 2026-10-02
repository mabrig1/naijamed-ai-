export async function sendTermiiSms(to: string, message: string) {
  const apiKey = process.env.TERMII_API_KEY;
  const baseUrl = process.env.TERMII_BASE_URL;
  const from = process.env.TERMII_SENDER_ID || "MediNaija";

  if (!apiKey || !baseUrl) throw new Error("Termii is not configured");

  const response = await fetch(baseUrl.replace(/\/$/, "") + "/api/sms/send", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      to,
      from,
      sms: message,
      type: "plain",
      channel: "generic",
      api_key: apiKey
    }),
    cache: "no-store"
  });

  if (!response.ok) throw new Error("Termii SMS request failed");
  return response.json();
}
