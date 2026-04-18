const faqEntries = [
  {
    id: "stalls_count",
    keywords: ["how many stalls", "stalls count", "total stalls", "stall count"],
    answer: "There are 97 stalls plus table space.",
  },
  {
    id: "travel_agents",
    keywords: ["travel agents", "how many agents", "agents attending"],
    answer: "1,000+ travel agents from all over the country will attend.",
  },
  {
    id: "attendee_regions",
    keywords: ["which regions", "from where", "attendees from", "regions attending"],
    answer: "Participants will come from throughout India, mainly South India.",
  },
  {
    id: "stall_sizes",
    keywords: ["sizes of stalls", "stall sizes", "stall size"],
    answer: "Available stall sizes are 2x3, 3x3, and 6x3.",
  },
  {
    id: "pricing",
    keywords: ["price", "pricing", "cost", "discount", "offer", "gst"],
    answer:
      "Price structure:\n- 2x3: INR 30,000 + 18% GST\n- 3x3: INR 40,000 + 18% GST\n- 6x3: INR 52,500 + 18% GST",
  },
  {
    id: "attendance",
    keywords: ["how many people", "visitors", "b2b count", "attendance"],
    answer: "Expected turnout: 10,000+ visitors. B2B: 1 (as per provided data).",
  },
  {
    id: "event_schedule",
    keywords: ["event schedule", "dates", "when is event", "5th 6th 7th"],
    answer: "Event schedule: 5th, 6th, and 7th.",
  },
  {
    id: "past_mtms",
    keywords: ["past mtm", "how many mtm", "previous mtm"],
    answer: "4 MTMs were held in the past.",
  },
  {
    id: "location",
    keywords: ["location", "venue", "where is event", "address"],
    answer: "Venue: Jagannatha Center for Arts and Culture, Vijaynagar, Mysore.",
  },
  {
    id: "accommodation",
    keywords: ["accommodation", "stay", "hotel for attendees"],
    answer: "Accommodation is only available for Hosted Buyers.",
  },
  {
    id: "infrastructure",
    keywords: ["ac", "hall", "infrastructure", "stall ac"],
    answer: "The event is hosted in an AC hall.",
  },
  {
    id: "stall_deliverables",
    keywords: ["deliverables", "what do stall owners get", "stall includes", "facilities for stall"],
    answer:
      "Deliverables for stall owners:\n- 2 chairs\n- 1 table\n- Welcome kit\n- 2 members per stall allowed\n- ID cards",
  },
  {
    id: "billing",
    keywords: ["billing", "invoice", "receipt", "payment"],
    answer:
      "Billing details:\n- Before payment: Proforma Invoice\n- After payment: Invoice and Receipt",
  },
  {
    id: "featured_events",
    keywords: ["featured events", "events", "activities", "programs"],
    answer:
      "Featured events include B2B meetings, B2C engagement, cultural events, symposiums, panel discussions, and award night.",
  },
  {
    id: "categories",
    keywords: ["categories", "who can participate", "sectors"],
    answer:
      "Categories include Travel Agents, Hotel Sector, Hospitality Brands, Destination Promoters, Travel & Tech companies, Tourism Colleges, Medical Tourism, Investors, and Policy Makers.",
  },
  {
    id: "key_segments",
    keywords: ["tourism segments", "key segments", "focus areas"],
    answer:
      "Key tourism segments: Heritage, Wildlife, Wellness and Yoga, Medical Tourism, Rural and Experiential Tourism.",
  },
  {
    id: "booking_poc",
    keywords: ["poc", "contact", "stall booking", "phone number", "email", "website"],
    answer:
      "Stall booking POC:\n- 9036824443 / 9035385672\n- info@mysoretravelmart.com\n- mysoretravelmart.com",
  },
  {
    id: "committee",
    keywords: ["organizing committee", "organisers", "committee members"],
    answer:
      "Organizing Committee:\n- B S Prashanth (Mysuru Travels Association)\n- C A Jayakumar (SKAL International Mysuru)\n- C Narayanagowda (Hotel Owners' Association)",
  },
  {
    id: "connectivity",
    keywords: ["connectivity", "airport", "train", "road", "reach mysore"],
    answer:
      "Connectivity:\n- Domestic airport\n- Vande Bharat train\n- 2.5 hours by road from BLR airport",
  },
  {
    id: "association",
    keywords: ["in association with", "partners", "supported by"],
    answer:
      "Event in association with Incredible India, Karnataka Tourism, Karnataka Tourism Forum, Karnataka Tourism Society, Mysore Hotel Owners' Association, SKAL International Mysuru, and Mysore Chamber of Commerce and Industries.",
  },
];

function normalizeText(text) {
  return (text || "").toLowerCase().replace(/[^\w\s+&-]/g, " ").replace(/\s+/g, " ").trim();
}

function scoreMatch(message, entry) {
  return entry.keywords.reduce((score, keyword) => {
    const normalizedKeyword = normalizeText(keyword);
    if (!normalizedKeyword) return score;
    return message.includes(normalizedKeyword) ? score + normalizedKeyword.length : score;
  }, 0);
}

function findBestAnswer(userMessage) {
  const normalized = normalizeText(userMessage);
  if (!normalized) return null;

  let bestEntry = null;
  let bestScore = 0;

  for (const entry of faqEntries) {
    const currentScore = scoreMatch(normalized, entry);
    if (currentScore > bestScore) {
      bestScore = currentScore;
      bestEntry = entry;
    }
  }

  // A tiny threshold avoids random false positives.
  if (!bestEntry || bestScore < 5) return null;
  return bestEntry.answer;
}

module.exports = {
  faqEntries,
  findBestAnswer,
};
