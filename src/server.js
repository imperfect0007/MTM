require("dotenv").config();

const crypto = require("crypto");
const express = require("express");
const { faqEntries, findBestAnswer } = require("./faqData");

const app = express();
const port = Number(process.env.PORT || 3000);
const verifyToken = process.env.WHATSAPP_VERIFY_TOKEN || "";
const accessToken = process.env.WHATSAPP_ACCESS_TOKEN || "";
const phoneNumberId = process.env.WHATSAPP_PHONE_NUMBER_ID || "";
const appSecret = process.env.WHATSAPP_APP_SECRET || "";

app.use(
  express.json({
    verify: (req, _res, buffer) => {
      req.rawBody = buffer;
    },
  })
);

function helpText() {
  return [
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
  ].join("\n");
}

function moreMenuText() {
  return [
    "More MTM FAQ options:",
    "11. Billing queries",
    "12. Featured events",
    "13. Categories",
    "14. Key tourism segments",
    "15. Stall booking contact",
    "16. Connectivity",
    "",
    "Type *menu* for main options.",
  ].join("\n");
}

function unknownText() {
  return [
    "I could not find that in MTM FAQs.",
    "Reply with *menu* to view numbered options, or contact:",
    "9036824443 / 9035385672",
    "info@mysoretravelmart.com",
    "mysoretravelmart.com",
  ].join("\n");
}

const idToAnswer = new Map(faqEntries.map((entry) => [entry.id, entry.answer]));

const menuNumberToId = {
  "1": "stalls_count",
  "2": "travel_agents",
  "3": "attendee_regions",
  "4": "stall_sizes",
  "5": "pricing",
  "6": "attendance",
  "7": "event_schedule",
  "8": "location",
  "9": "accommodation",
  "10": "stall_deliverables",
  "11": "billing",
  "12": "featured_events",
  "13": "categories",
  "14": "key_segments",
  "15": "booking_poc",
  "16": "connectivity",
};

function answerByMenuNumber(numberText) {
  const faqId = menuNumberToId[numberText];
  if (!faqId) return null;
  return idToAnswer.get(faqId) || null;
}

function isValidMetaSignature(req) {
  const signatureHeader = req.get("x-hub-signature-256") || "";
  if (!signatureHeader.startsWith("sha256=")) return false;
  if (!appSecret || !req.rawBody) return false;

  const receivedSignature = signatureHeader.slice(7);
  const expectedSignature = crypto.createHmac("sha256", appSecret).update(req.rawBody).digest("hex");

  const receivedBuffer = Buffer.from(receivedSignature, "utf8");
  const expectedBuffer = Buffer.from(expectedSignature, "utf8");
  if (receivedBuffer.length !== expectedBuffer.length) return false;

  return crypto.timingSafeEqual(receivedBuffer, expectedBuffer);
}

function buildReplyText(incomingText) {
  const incoming = (incomingText || "").trim();
  const lowered = incoming.toLowerCase();

  if (!incoming || ["hi", "hello", "hey", "help", "menu", "start"].includes(lowered)) {
    return helpText();
  }

  if (["more", "next", "options"].includes(lowered)) {
    return moreMenuText();
  }

  if (/^\d{1,2}$/.test(lowered)) {
    return answerByMenuNumber(lowered) || "Invalid option. Type *menu* to see available options.";
  }

  return findBestAnswer(incoming) || unknownText();
}

async function sendWhatsAppText(to, text) {
  if (!to || !text) return;
  if (!accessToken || !phoneNumberId) {
    console.warn("Missing WHATSAPP_ACCESS_TOKEN or WHATSAPP_PHONE_NUMBER_ID.");
    return;
  }

  const endpoint = `https://graph.facebook.com/v22.0/${phoneNumberId}/messages`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      messaging_product: "whatsapp",
      to,
      type: "text",
      text: { body: text },
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Meta API error ${response.status}: ${errorBody}`);
  }
}

app.get("/", (_req, res) => {
  res.status(200).json({ ok: true, service: "MTM WhatsApp FAQ Bot" });
});

app.get("/webhook/whatsapp", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  if (mode === "subscribe" && token === verifyToken) {
    res.status(200).send(challenge);
    return;
  }

  res.sendStatus(403);
});

app.post("/webhook/whatsapp", async (req, res) => {
  if (!appSecret) {
    console.error("Missing WHATSAPP_APP_SECRET.");
    res.sendStatus(500);
    return;
  }

  if (!isValidMetaSignature(req)) {
    console.warn("Invalid webhook signature.");
    res.sendStatus(403);
    return;
  }

  res.sendStatus(200);

  try {
    const entry = req.body?.entry?.[0];
    const change = entry?.changes?.[0];
    const value = change?.value;
    const message = value?.messages?.[0];

    if (!message || message.type !== "text") return;

    const from = message.from;
    const incomingText = message.text?.body || "";
    const replyText = buildReplyText(incomingText);
    await sendWhatsAppText(from, replyText);
  } catch (error) {
    console.error("Webhook processing failed:", error.message);
  }
});

app.listen(port, () => {
  console.log(`MTM WhatsApp FAQ Bot listening on http://localhost:${port}`);
});
