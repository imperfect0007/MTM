# MTM WhatsApp FAQ Bot (FastAPI)

A FastAPI backend for Mysore Travel Mart (MTM) WhatsApp FAQ automation using Meta WhatsApp Cloud API.

It supports:
- menu-driven replies (`1` to `16`)
- free-text FAQ matching
- Meta webhook verification (`GET /webhook/whatsapp`)
- Meta signature validation (`X-Hub-Signature-256`) on incoming webhooks

## 1) Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configure environment

Copy `.env.example` to `.env` and set:

```bash
PORT=3000
WHATSAPP_VERIFY_TOKEN=mtm_verify_token_123
WHATSAPP_ACCESS_TOKEN=EAAGxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_APP_SECRET=your_meta_app_secret
```

## 3) Run locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

## 4) API endpoints

- `GET /` health check
- `GET /webhook/whatsapp` Meta webhook verification
- `POST /webhook/whatsapp` incoming WhatsApp events

## 5) Deploy on Render

This repo includes `render.yaml` for Python runtime:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set these env vars in Render:
- `WHATSAPP_VERIFY_TOKEN`
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_APP_SECRET`

## 6) Configure in Meta Developers

1. Open [Meta for Developers](https://developers.facebook.com/) and your app.
2. Add WhatsApp product.
3. Webhook settings:
   - Callback URL: `https://<your-render-service>.onrender.com/webhook/whatsapp`
   - Verify token: same as `WHATSAPP_VERIFY_TOKEN`
4. Subscribe to `messages`.
5. From API Setup:
   - Copy Phone Number ID to `WHATSAPP_PHONE_NUMBER_ID`
   - Copy Access Token to `WHATSAPP_ACCESS_TOKEN`
6. From App Settings -> Basic:
   - Copy App Secret to `WHATSAPP_APP_SECRET`

## Menu flow

- `hi` or `menu` -> options 1-10
- `more` -> options 11-16
- `5` -> pricing answer
- free text also works (example: `Where is the venue?`)
