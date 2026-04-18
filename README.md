# MTM WhatsApp FAQ Bot

A simple WhatsApp FAQ bot for Mysore Travel Mart (MTM), preloaded with event FAQs.

It supports both:
- menu-driven replies (`1`, `2`, ... `16`)
- free-text FAQ questions (keyword matching)

## 1) Install

```bash
npm install
```

## 2) Configure environment

Copy `.env.example` to `.env` and update values:

```bash
PORT=3000
WHATSAPP_VERIFY_TOKEN=mtm_verify_token_123
WHATSAPP_ACCESS_TOKEN=EAAGxxxxxxxxxxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_APP_SECRET=your_meta_app_secret
```

Get these from Meta Developers:
- `WHATSAPP_VERIFY_TOKEN`: your custom secret string
- `WHATSAPP_ACCESS_TOKEN`: temporary/permanent access token
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp phone number ID
- `WHATSAPP_APP_SECRET`: Meta App Secret (used to verify webhook signature)

## 3) Run locally

```bash
npm run dev
```

Webhook endpoints:

- `GET /webhook/whatsapp` (verification)
- `POST /webhook/whatsapp` (incoming messages)

Health check:

`GET /`

## 4) Deploy backend on Render

1. Push this project to GitHub.
2. In Render, create **New + -> Web Service**.
3. Connect your repo.
4. Configure:
   - Runtime: `Node`
   - Build command: `npm install`
   - Start command: `npm start`
5. Add environment variables in Render:
   - `WHATSAPP_VERIFY_TOKEN`
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_APP_SECRET`
6. Deploy and copy your Render URL:
   - `https://<your-render-service>.onrender.com`

## 5) Connect WhatsApp number in Meta Developers

1. Go to [Meta for Developers](https://developers.facebook.com/) and open your app.
2. Add **WhatsApp** product (if not already).
3. In WhatsApp -> **Configuration**:
   - Callback URL: `https://<your-render-service>.onrender.com/webhook/whatsapp`
   - Verify token: same value as `WHATSAPP_VERIFY_TOKEN`
4. Subscribe webhook field: `messages`.
5. In WhatsApp -> API Setup:
   - Copy `Phone number ID` -> set `WHATSAPP_PHONE_NUMBER_ID`
   - Generate/copy access token -> set `WHATSAPP_ACCESS_TOKEN`
6. In Meta app -> Settings -> Basic:
   - Copy `App Secret` -> set `WHATSAPP_APP_SECRET`
7. Add recipient phone numbers (for test mode) and send `hi` to your WhatsApp number.

## Menu Flow

- Send `hi` or `menu` to view options 1-10
- Send `more` for options 11-16
- Reply with option number (example: `5` for pricing)
- Send `menu` anytime to restart menu
- You can type natural language too (example: "Where is the venue?")

## Example Questions

- How many stalls are there?
- What is the stall pricing?
- Where is the venue?
- What are event dates?
- Who should I contact for stall booking?

## Customize FAQs

Update `src/faqData.js`:

- Add/modify `keywords` to improve matching.
- Update `answer` text as needed.

## Notes

- Matching is keyword-based and lightweight.
- Incoming webhook requests are verified using `X-Hub-Signature-256`.
- For high-scale production, add:
  - DB logging
  - intent classification (NLP/LLM)
  - rate limiting
