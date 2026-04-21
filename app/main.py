import hashlib
import hmac
import json
import os
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.faq_data import ID_TO_ANSWER, MENU_NUMBER_TO_ID, find_best_answer

load_dotenv()

app = FastAPI(title="MTM WhatsApp FAQ Bot")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")


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


@app.get("/")
async def health() -> Dict[str, Any]:
    return {"ok": True, "service": "MTM WhatsApp FAQ Bot (FastAPI)"}


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
        reply_text = build_reply_text(incoming_text)
        await send_whatsapp_text(from_number, reply_text)
    except Exception as exc:
        payload_preview = json.dumps(payload, ensure_ascii=True)[:1200]
        print(f"Webhook processing failed: {exc}. payload={payload_preview}")

    return JSONResponse(content={"ok": True}, status_code=200)
