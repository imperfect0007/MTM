import hashlib
import hmac
import json
import os
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.responses import FileResponse

from app.faq_data import ID_TO_ANSWER, MENU_NUMBER_TO_ID, find_best_answer

load_dotenv()

app = FastAPI(title="MTM WhatsApp FAQ Bot")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")

# Admin numbers that should receive stall enquiries (comma-separated).
ADMIN_NUMBERS = [
    n.strip().replace(" ", "")
    for n in os.getenv("ADMIN_NUMBERS", "9449865970,9036739808").split(",")
    if n.strip()
]

FLOOR_PLAN_FILENAME = "MTM_Floor_plan.pdf"
FLOOR_PLAN_PATH = (Path(__file__).resolve().parents[1] / FLOOR_PLAN_FILENAME).resolve()

# Public base URL used to build downloadable links (Render service URL).
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")

# Very small in-memory conversation state (resets on deploy/restart).
USER_NAME_BY_NUMBER: dict[str, str] = {}
USER_STATE_BY_NUMBER: dict[str, str] = {}  # "awaiting_name" | "awaiting_enquiry"


def get_public_base_url() -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    if KEEPALIVE_URL:
        parsed = urlparse(KEEPALIVE_URL)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    return ""


def looks_like_floor_plan_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(k in lowered for k in ["floor plan", "floorplan", "layout", "stall layout", "plan pdf", "pdf plan"])


def looks_like_stall_enquiry(text: str) -> bool:
    lowered = (text or "").lower()
    return any(
        k in lowered
        for k in [
            "stall",
            "book stall",
            "stall booking",
            "need stall",
            "enquire",
            "enquiry",
            "enquire stall",
            "stall enquiry",
        ]
    )


def start_stall_enquiry(from_number: str) -> Optional[str]:
    if not from_number:
        return None
    if from_number in USER_NAME_BY_NUMBER and USER_NAME_BY_NUMBER[from_number].strip():
        USER_STATE_BY_NUMBER[from_number] = "awaiting_enquiry"
        return "Please share your stall requirement / enquiry details."
    USER_STATE_BY_NUMBER[from_number] = "awaiting_name"
    return "Sure. Please tell me your name."


def handle_stall_enquiry_state(from_number: str, incoming_text: str) -> Optional[str]:
    state = USER_STATE_BY_NUMBER.get(from_number)
    text = (incoming_text or "").strip()
    if not state:
        return None

    if state == "awaiting_name":
        if not text:
            return "Please tell me your name."
        USER_NAME_BY_NUMBER[from_number] = text
        USER_STATE_BY_NUMBER[from_number] = "awaiting_enquiry"
        return f"Thanks, {text}. Please share your stall requirement / enquiry details."

    if state == "awaiting_enquiry":
        if not text:
            return "Please share your stall requirement / enquiry details."
        USER_STATE_BY_NUMBER.pop(from_number, None)
        name = USER_NAME_BY_NUMBER.get(from_number, "").strip() or "N/A"
        forward = "\n".join(
            [
                "New stall enquiry",
                f"Name: {name}",
                f"WhatsApp: {from_number}",
                f"Message: {text}",
            ]
        )
        return "__FORWARD_TO_ADMINS__" + forward

    return None

# Keep-alive support:
# - Render (and similar platforms) can put idle services to sleep.
# - A running service can ping itself, but self-pings won't wake a sleeping service.
# - Use an external monitor (UptimeRobot, cron-job.org, GitHub Actions) to hit /ping.
KEEPALIVE_URL = os.getenv("KEEPALIVE_URL", "").strip()
KEEPALIVE_INTERVAL_SECONDS = int(os.getenv("KEEPALIVE_INTERVAL_SECONDS", "50"))
ENABLE_SELF_PING = os.getenv("ENABLE_SELF_PING", "").strip().lower() in {"1", "true", "yes", "on"}


async def keepalive_loop() -> None:
    url = KEEPALIVE_URL or ""
    if not url:
        return
    interval = max(10, KEEPALIVE_INTERVAL_SECONDS)

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                resp = await client.get(url)
                print(f"Keepalive ping {url} -> {resp.status_code}")
            except Exception as exc:
                print(f"Keepalive ping failed for {url}: {exc}")
            await asyncio.sleep(interval)


@app.on_event("startup")
async def _startup_keepalive() -> None:
    if ENABLE_SELF_PING and (KEEPALIVE_URL or "").strip():
        asyncio.create_task(keepalive_loop())


def help_text() -> str:
    return "\n".join(
        [
            "Hello from MTM FAQ Bot.",
            "",
            "Reply with a number:",
            "1. Stalls count",
            "2. Travel agents count",
            "3. Regions attending",
            "4. Stall sizes",
            "5. Price structure",
            "6. Event attendance",
            "7. Event schedule",
            "8. Venue details",
            "9. Accommodation",
            "10. Stall deliverables",
            "",
            "Type *more* for options 11-16.",
            "Type *menu* anytime to see this again.",
            "",
            "You can also type your question directly.",
        ]
    )


def more_menu_text() -> str:
    return "\n".join(
        [
            "More MTM FAQ options:",
            "11. Billing queries",
            "12. Featured events",
            "13. Categories",
            "14. Key tourism segments",
            "15. Stall booking contact",
            "16. Connectivity",
            "",
            "Type *menu* for main options.",
        ]
    )


def unknown_text() -> str:
    return "\n".join(
        [
            "I could not find that in MTM FAQs.",
            "Reply with *menu* to view numbered options, or contact:",
            "9036824443 / 9035385672",
            "info@mysoretravelmart.com",
            "mysoretravelmart.com",
        ]
    )


def answer_by_menu_number(number_text: str) -> str | None:
    faq_id = MENU_NUMBER_TO_ID.get(number_text)
    if not faq_id:
        return None
    answer = ID_TO_ANSWER.get(faq_id)
    return str(answer) if answer else None


def build_reply_text(incoming_text: str) -> str:
    incoming = (incoming_text or "").strip()
    lowered = incoming.lower()

    if not incoming or lowered in {"hi", "hello", "hey", "help", "menu", "start"}:
        return help_text()

    if lowered in {"more", "next", "options"}:
        return more_menu_text()

    if lowered.isdigit() and len(lowered) <= 2:
        return answer_by_menu_number(lowered) or "Invalid option. Type *menu* to see available options."

    return find_best_answer(incoming) or unknown_text()


def is_valid_meta_signature(raw_body: bytes, signature_header: str) -> bool:
    if not APP_SECRET:
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    received_signature = signature_header[7:]
    expected_signature = hmac.new(APP_SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    return hmac.compare_digest(received_signature, expected_signature)


async def send_whatsapp_text(to: str, text: str) -> None:
    if not to or not text:
        return
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID.")
        return

    endpoint = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(endpoint, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Message sent to {to}. Meta response status={response.status_code}")
        except httpx.HTTPStatusError as exc:
            body_preview = exc.response.text[:500]
            print(
                "Meta API HTTP error while sending message. "
                f"status={exc.response.status_code}, body={body_preview}"
            )
            raise
        except Exception as exc:
            print(f"Unexpected error while sending WhatsApp message: {exc}")
            raise


async def send_whatsapp_document(to: str, link: str, filename: str) -> None:
    if not to or not link:
        return
    if not ACCESS_TOKEN or not PHONE_NUMBER_ID:
        print("Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID.")
        return

    endpoint = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {"link": link, "filename": filename},
    }
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        print(f"Document sent to {to}. Meta response status={response.status_code}")


@app.get("/")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "MTM WhatsApp FAQ Bot (FastAPI)"}


@app.get("/ping")
async def ping() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/floor-plan")
async def floor_plan() -> FileResponse:
    return FileResponse(path=str(FLOOR_PLAN_PATH), filename=FLOOR_PLAN_FILENAME)


@app.get("/webhook/whatsapp")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(content=challenge, status_code=200)
    return PlainTextResponse(content="Forbidden", status_code=403)


@app.post("/webhook/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    raw_body = await request.body()
    signature_header = request.headers.get("x-hub-signature-256", "")

    if not APP_SECRET:
        return PlainTextResponse(content="Missing WHATSAPP_APP_SECRET", status_code=500)

    if not is_valid_meta_signature(raw_body, signature_header):
        print("Invalid Meta signature for incoming webhook request.")
        return PlainTextResponse(content="Invalid signature", status_code=403)

    payload = await request.json()

    try:
        entry = payload.get("entry", [{}])[0]
        change = entry.get("changes", [{}])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])
        statuses = value.get("statuses", [])

        if not messages:
            if statuses:
                print("Received status update event (no inbound message).")
            else:
                print("Webhook event without messages/statuses.")
            return JSONResponse(content={"ok": True}, status_code=200)

        message = messages[0]
        if message.get("type") != "text":
            print(f"Ignoring non-text message type={message.get('type')}")
            return JSONResponse(content={"ok": True}, status_code=200)

        from_number = message.get("from", "")
        incoming_text = message.get("text", {}).get("body", "")
        print(f"Incoming message from {from_number}: {incoming_text!r}")

        # 1) If user is mid-enquiry flow, continue it.
        state_reply = handle_stall_enquiry_state(from_number, incoming_text)
        if state_reply:
            if state_reply.startswith("__FORWARD_TO_ADMINS__"):
                forward_text = state_reply.replace("__FORWARD_TO_ADMINS__", "", 1)
                for admin in ADMIN_NUMBERS:
                    await send_whatsapp_text(admin, forward_text)
                await send_whatsapp_text(from_number, "Thanks. Your enquiry has been shared with our team.")
            else:
                await send_whatsapp_text(from_number, state_reply)
            return JSONResponse(content={"ok": True}, status_code=200)

        # 2) If floor plan requested, send PDF link.
        if looks_like_floor_plan_request(incoming_text):
            base = get_public_base_url()
            if base:
                link = f"{base}/floor-plan"
                await send_whatsapp_document(from_number, link=link, filename=FLOOR_PLAN_FILENAME)
            else:
                await send_whatsapp_text(from_number, "Floor plan is available. Please ask the organizer for the PDF.")

            # If they are also enquiring about stalls, start enquiry flow.
            if looks_like_stall_enquiry(incoming_text):
                prompt = start_stall_enquiry(from_number)
                if prompt:
                    await send_whatsapp_text(from_number, prompt)
            return JSONResponse(content={"ok": True}, status_code=200)

        # 3) If stall enquiry detected, start enquiry flow (ask name first).
        if looks_like_stall_enquiry(incoming_text):
            prompt = start_stall_enquiry(from_number)
            if prompt:
                await send_whatsapp_text(from_number, prompt)
            return JSONResponse(content={"ok": True}, status_code=200)

        # 4) Default FAQ response.
        reply_text = build_reply_text(incoming_text)
        await send_whatsapp_text(from_number, reply_text)
    except Exception as exc:
        payload_preview = json.dumps(payload, ensure_ascii=True)[:1200]
        print(f"Webhook processing failed: {exc}. payload={payload_preview}")

    return JSONResponse(content={"ok": True}, status_code=200)
