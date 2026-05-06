"""
Notification Service — NaijaMed AI
Email (SMTP / SendGrid) + SMS (Termii API) notifications for the Export Engine.

NOTE: Real credentials must be set in .env before notifications are delivered.
Mock mode (no credentials): logs to stdout only, returns success=False with reason.

Email channels:
  - Primary: SendGrid HTTP API (SENDGRID_API_KEY)
  - Fallback: SMTP (SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD)

SMS channel:
  - Termii API (TERMII_API_KEY) — Nigerian SMS gateway, supports international numbers
  - Termii docs: https://developers.termii.com/
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Literal

import httpx

from ..core.config import settings

logger = logging.getLogger("notification_service")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmailResult:
    success: bool
    channel: Literal["sendgrid", "smtp", "mock"] = "mock"
    error: str | None = None


@dataclass
class SMSResult:
    success: bool
    channel: Literal["termii", "mock"] = "mock"
    message_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Email — SendGrid HTTP API
# ---------------------------------------------------------------------------

_SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
_FROM_EMAIL = "noreply@naijamed.ai"
_FROM_NAME  = "NaijaMed AI"


def _send_via_sendgrid(to_email: str, subject: str, html_body: str, plain_body: str) -> EmailResult:
    """Send email using SendGrid HTTP API."""
    api_key = getattr(settings, "SENDGRID_API_KEY", "")
    if not api_key:
        return EmailResult(success=False, channel="sendgrid", error="SENDGRID_API_KEY not configured")

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": _FROM_EMAIL, "name": _FROM_NAME},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": plain_body},
            {"type": "text/html",  "value": html_body},
        ],
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                _SENDGRID_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
        resp.raise_for_status()
        return EmailResult(success=True, channel="sendgrid")
    except Exception as exc:
        logger.error("SendGrid error: %s", exc)
        return EmailResult(success=False, channel="sendgrid", error=str(exc))


# ---------------------------------------------------------------------------
# Email — SMTP fallback
# ---------------------------------------------------------------------------

def _send_via_smtp(to_email: str, subject: str, html_body: str, plain_body: str) -> EmailResult:
    """Send email using SMTP with TLS."""
    smtp_host     = getattr(settings, "SMTP_HOST", "")
    smtp_port     = getattr(settings, "SMTP_PORT", 587)
    smtp_user     = getattr(settings, "SMTP_USER", "")
    smtp_password = getattr(settings, "SMTP_PASSWORD", "")

    if not smtp_host or not smtp_user:
        return EmailResult(success=False, channel="smtp", error="SMTP not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{_FROM_NAME} <{smtp_user}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body,  "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, int(smtp_port)) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return EmailResult(success=True, channel="smtp")
    except Exception as exc:
        logger.error("SMTP error: %s", exc)
        return EmailResult(success=False, channel="smtp", error=str(exc))


# ---------------------------------------------------------------------------
# Email — public dispatcher (tries SendGrid, falls back to SMTP)
# ---------------------------------------------------------------------------

def send_email(to_email: str, subject: str, html_body: str, plain_body: str = "") -> EmailResult:
    """
    Send an email.  Tries SendGrid first, falls back to SMTP.
    If neither is configured: logs a warning and returns success=False.
    """
    if not plain_body:
        # Rudimentary HTML → plain text strip
        import re
        plain_body = re.sub(r"<[^>]+>", "", html_body).strip()

    result = _send_via_sendgrid(to_email, subject, html_body, plain_body)
    if result.success:
        return result

    result2 = _send_via_smtp(to_email, subject, html_body, plain_body)
    if result2.success:
        return result2

    # Neither channel available — log and return failure
    logger.warning(
        "Email NOT sent to %s (subject: %s). SendGrid: %s | SMTP: %s",
        to_email, subject, result.error, result2.error,
    )
    return EmailResult(success=False, channel="mock", error="No email channel configured")


# ---------------------------------------------------------------------------
# SMS — Termii API
# ---------------------------------------------------------------------------

_TERMII_BASE_URL = "https://api.ng.termii.com/api"

def send_sms(phone: str, message: str, sender_id: str = "NaijaMed") -> SMSResult:
    """
    Send an SMS via Termii API.

    phone: E.164 format recommended (e.g., +2348012345678).
           Termii also accepts local format (08012345678).
    sender_id: 11-char alphanumeric sender ID registered with Termii.

    Real API: POST https://api.ng.termii.com/api/sms/send
    Docs:     https://developers.termii.com/messaging
    """
    api_key  = getattr(settings, "TERMII_API_KEY",   "")
    base_url = getattr(settings, "TERMII_BASE_URL",  _TERMII_BASE_URL)

    if not api_key:
        logger.warning("SMS NOT sent to %s — TERMII_API_KEY not configured. Message: %s", phone, message)
        return SMSResult(success=False, channel="mock", error="TERMII_API_KEY not configured")

    payload = {
        "to":         phone,
        "from":       sender_id,
        "sms":        message,
        "type":       "plain",
        "channel":    "generic",
        "api_key":    api_key,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(f"{base_url}/sms/send", json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data.get("message_id") or data.get("data", {}).get("message_id")
        return SMSResult(success=True, channel="termii", message_id=str(msg_id) if msg_id else None)
    except Exception as exc:
        logger.error("Termii SMS error to %s: %s", phone, exc)
        return SMSResult(success=False, channel="termii", error=str(exc))


# ---------------------------------------------------------------------------
# Typed notification helpers
# ---------------------------------------------------------------------------

def notify_new_trade_inquiry(
    seller_email: str,
    seller_phone: str | None,
    seller_name: str,
    herb_name: str,
    quantity_kg: float,
    buyer_name: str,
    inquiry_id: int,
) -> dict[str, Any]:
    """Notify seller of a new trade inquiry from a global buyer."""
    subject = f"[NaijaMed] New Inquiry for {herb_name} — {quantity_kg} kg"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">📬 New Trade Inquiry</h2>
      <p>Dear <strong>{seller_name}</strong>,</p>
      <p>A global buyer has submitted a trade inquiry for your listing:</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Herb</td><td style="padding:6px"><strong>{herb_name}</strong></td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Quantity</td><td style="padding:6px">{quantity_kg:,.1f} kg</td></tr>
        <tr><td style="padding:6px;color:#555">Buyer</td><td style="padding:6px">{buyer_name}</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Inquiry ID</td><td style="padding:6px">#{inquiry_id}</td></tr>
      </table>
      <p style="margin-top:20px">
        <a href="https://naijamed.ai/export/inquiries/{inquiry_id}"
           style="background:#1a5c38;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
          View Inquiry →
        </a>
      </p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = f"New trade inquiry #{inquiry_id} for {herb_name} ({quantity_kg} kg) from {buyer_name}. Log in to respond."
    email_result = send_email(seller_email, subject, html, plain)

    sms_result = None
    if seller_phone:
        sms_msg = f"NaijaMed: New inquiry for {herb_name} ({quantity_kg}kg) from {buyer_name}. Ref #{inquiry_id}. naijamed.ai"
        sms_result = send_sms(seller_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_order_confirmed(
    buyer_email: str,
    buyer_phone: str | None,
    buyer_name: str,
    herb_name: str,
    quantity_kg: float,
    total_usd: float,
    order_id: int,
    escrow_id: str,
) -> dict[str, Any]:
    """Notify buyer that order is confirmed and escrow is active."""
    subject = f"[NaijaMed] Order Confirmed — {herb_name} #{order_id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">✅ Order Confirmed</h2>
      <p>Dear <strong>{buyer_name}</strong>,</p>
      <p>Your order has been confirmed and funds are held in escrow.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Order ID</td><td style="padding:6px">#{order_id}</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Herb</td><td style="padding:6px">{herb_name}</td></tr>
        <tr><td style="padding:6px;color:#555">Quantity</td><td style="padding:6px">{quantity_kg:,.1f} kg</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Total Value</td><td style="padding:6px"><strong>${total_usd:,.2f} USD</strong></td></tr>
        <tr><td style="padding:6px;color:#555">Escrow Ref</td><td style="padding:6px">{escrow_id}</td></tr>
      </table>
      <p style="margin-top:20px">Funds will be released to the seller upon your delivery confirmation.</p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = f"Order #{order_id} confirmed. {herb_name} ({quantity_kg} kg) — ${total_usd:.2f}. Escrow: {escrow_id}"
    email_result = send_email(buyer_email, subject, html, plain)

    sms_result = None
    if buyer_phone:
        sms_msg = f"NaijaMed: Order #{order_id} confirmed. {herb_name} {quantity_kg}kg escrow active. naijamed.ai"
        sms_result = send_sms(buyer_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_shipment_departed(
    buyer_email: str,
    buyer_phone: str | None,
    buyer_name: str,
    herb_name: str,
    tracking_number: str,
    carrier: str,
    estimated_arrival: str,
    order_id: int,
) -> dict[str, Any]:
    """Notify buyer that shipment has departed Nigeria."""
    subject = f"[NaijaMed] Shipment Departed — Order #{order_id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">🚢 Shipment Departed</h2>
      <p>Dear <strong>{buyer_name}</strong>,</p>
      <p>Your order of <strong>{herb_name}</strong> has been shipped from Nigeria.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Tracking #</td><td style="padding:6px"><strong>{tracking_number}</strong></td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Carrier</td><td style="padding:6px">{carrier}</td></tr>
        <tr><td style="padding:6px;color:#555">Est. Arrival</td><td style="padding:6px">{estimated_arrival}</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Order ID</td><td style="padding:6px">#{order_id}</td></tr>
      </table>
      <p style="margin-top:20px">
        <a href="https://naijamed.ai/logistics/tracker?tracking={tracking_number}"
           style="background:#1a5c38;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
          Track Shipment →
        </a>
      </p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = f"Shipment for Order #{order_id} departed. Tracking: {tracking_number} via {carrier}. ETA: {estimated_arrival}"
    email_result = send_email(buyer_email, subject, html, plain)

    sms_result = None
    if buyer_phone:
        sms_msg = f"NaijaMed: Order #{order_id} shipped! Track: {tracking_number} ({carrier}). ETA {estimated_arrival}"
        sms_result = send_sms(buyer_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_customs_cleared(
    buyer_email: str,
    buyer_phone: str | None,
    buyer_name: str,
    herb_name: str,
    order_id: int,
    clearance_country: str,
) -> dict[str, Any]:
    """Notify buyer that customs clearance has been completed."""
    subject = f"[NaijaMed] Customs Cleared — Order #{order_id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">✅ Customs Cleared</h2>
      <p>Dear <strong>{buyer_name}</strong>,</p>
      <p>Your shipment of <strong>{herb_name}</strong> (Order #{order_id}) has cleared
      customs in <strong>{clearance_country}</strong>. Delivery is expected soon.</p>
      <p>
        <a href="https://naijamed.ai/logistics/tracker"
           style="background:#1a5c38;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
          View Shipment →
        </a>
      </p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = f"Order #{order_id}: customs cleared in {clearance_country}. Delivery expected soon."
    email_result = send_email(buyer_email, subject, html, plain)

    sms_result = None
    if buyer_phone:
        sms_msg = f"NaijaMed: Order #{order_id} customs cleared in {clearance_country}. Delivery expected soon."
        sms_result = send_sms(buyer_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_funds_released(
    seller_email: str,
    seller_phone: str | None,
    seller_name: str,
    herb_name: str,
    amount_usd: float,
    order_id: int,
) -> dict[str, Any]:
    """Notify seller that escrow funds have been released."""
    subject = f"[NaijaMed] 💰 Funds Released — Order #{order_id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">💰 Funds Released</h2>
      <p>Dear <strong>{seller_name}</strong>,</p>
      <p>Escrow funds have been released to your account for Order #{order_id}.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Herb</td><td style="padding:6px">{herb_name}</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Amount Released</td>
          <td style="padding:6px"><strong style="color:#1a5c38">${amount_usd:,.2f} USD</strong></td></tr>
        <tr><td style="padding:6px;color:#555">Order ID</td><td style="padding:6px">#{order_id}</td></tr>
      </table>
      <p style="margin-top:16px;color:#555;font-size:14px">
        Funds will reflect in your bank account within 1–3 business days depending on your payment provider.
      </p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = f"Escrow funds released for Order #{order_id}: ${amount_usd:,.2f} USD for {herb_name}."
    email_result = send_email(seller_email, subject, html, plain)

    sms_result = None
    if seller_phone:
        sms_msg = f"NaijaMed: ${amount_usd:,.2f} released for Order #{order_id} ({herb_name}). Check your account. naijamed.ai"
        sms_result = send_sms(seller_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_temperature_breach(
    buyer_email: str,
    buyer_phone: str | None,
    buyer_name: str,
    herb_name: str,
    current_temp_c: float,
    threshold_c: float,
    shipment_id: int,
    tracking_number: str,
) -> dict[str, Any]:
    """Alert buyer (and potentially seller) of a cold-chain temperature breach."""
    subject = f"[NaijaMed] ⚠️ Temperature Alert — Shipment #{shipment_id}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#c0392b">⚠️ Temperature Breach Alert</h2>
      <p>Dear <strong>{buyer_name}</strong>,</p>
      <p>A temperature breach has been detected for your shipment of <strong>{herb_name}</strong>.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Current Temp</td>
          <td style="padding:6px"><strong style="color:#c0392b">{current_temp_c:.1f}°C</strong></td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Safe Threshold</td>
          <td style="padding:6px">{threshold_c:.1f}°C</td></tr>
        <tr><td style="padding:6px;color:#555">Tracking #</td><td style="padding:6px">{tracking_number}</td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Shipment ID</td>
          <td style="padding:6px">#{shipment_id}</td></tr>
      </table>
      <p style="margin-top:16px">Please contact our logistics team immediately if you wish to raise a dispute.</p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria</p>
    </div>
    """
    plain = (
        f"TEMPERATURE ALERT: Shipment #{shipment_id} ({herb_name}) detected {current_temp_c:.1f}°C "
        f"(threshold: {threshold_c:.1f}°C). Tracking: {tracking_number}"
    )
    email_result = send_email(buyer_email, subject, html, plain)

    sms_result = None
    if buyer_phone:
        sms_msg = (
            f"NaijaMed ALERT: Shipment #{shipment_id} temp breach {current_temp_c:.1f}C "
            f"(max {threshold_c:.1f}C). Track: {tracking_number}"
        )
        sms_result = send_sms(buyer_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}


def notify_price_alert(
    user_email: str,
    user_phone: str | None,
    user_name: str,
    herb_name: str,
    current_price_usd: float,
    threshold_usd: float,
    direction: Literal["above", "below"],
    region: str,
) -> dict[str, Any]:
    """Alert user when herb price crosses their configured threshold."""
    direction_text = "risen above" if direction == "above" else "fallen below"
    icon = "📈" if direction == "above" else "📉"
    subject = f"[NaijaMed] {icon} Price Alert — {herb_name} in {region.title()}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px">
      <h2 style="color:#1a5c38">{icon} Price Alert: {herb_name}</h2>
      <p>Dear <strong>{user_name}</strong>,</p>
      <p>The price of <strong>{herb_name}</strong> has <strong>{direction_text}</strong> your
      threshold in the <strong>{region.title()}</strong> market.</p>
      <table style="border-collapse:collapse;width:100%">
        <tr><td style="padding:6px;color:#555">Current Price</td>
          <td style="padding:6px"><strong>${current_price_usd:.2f}/kg</strong></td></tr>
        <tr style="background:#f5f5f5"><td style="padding:6px;color:#555">Your Threshold</td>
          <td style="padding:6px">${threshold_usd:.2f}/kg</td></tr>
        <tr><td style="padding:6px;color:#555">Market Region</td><td style="padding:6px">{region.title()}</td></tr>
      </table>
      <p style="margin-top:20px">
        <a href="https://naijamed.ai/prices"
           style="background:#1a5c38;color:white;padding:10px 20px;text-decoration:none;border-radius:4px">
          View Price Intelligence →
        </a>
      </p>
      <hr style="margin-top:30px;border:none;border-top:1px solid #eee"/>
      <p style="font-size:12px;color:#999">NaijaMed AI · Abuja, Nigeria · Unsubscribe from price alerts in your account settings.</p>
    </div>
    """
    plain = (
        f"Price Alert: {herb_name} has {direction_text} ${threshold_usd:.2f}/kg "
        f"in {region} — currently ${current_price_usd:.2f}/kg."
    )
    email_result = send_email(user_email, subject, html, plain)

    sms_result = None
    if user_phone:
        sms_msg = (
            f"NaijaMed {icon}: {herb_name} now ${current_price_usd:.2f}/kg "
            f"({direction_text} ${threshold_usd:.2f} in {region}). naijamed.ai/prices"
        )
        sms_result = send_sms(user_phone, sms_msg)

    return {"email": email_result.__dict__, "sms": sms_result.__dict__ if sms_result else None}
