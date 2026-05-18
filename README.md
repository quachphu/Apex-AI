# Apex — AI Agent Receptionist

**Apex turns a cold lead into a qualified, followed-up, paid customer — fully autonomously.**

Built for the [YC Call My Agent Hackathon](https://www.ycombinator.com/) · May 17, 2026

---

Video Demo: https://youtu.be/bMP9iGPU7H0

## The Problem

Every B2C business has the same bottleneck: someone has to receive or call leads, qualify them, handle objections, send follow-ups, and collect payment. That pipeline takes a human SDR 45+ minutes per conversion. Most businesses can't afford to hire one. The ones that do convert less than 5% of cold leads because the follow-up is too slow.

## What Apex Does

Apex is an AI receptionist for local businesses that can receive inbound calls, cold-call leads, qualify them live, handle objections with real-time product context, and close the loop with follow-up email, booking, and payment. It’s simple for any local business to use: upload your leads or customer list, connect your business details, and let Apex handle the calls, follow-ups, bookings, and payments automatically.

```
Cold Lead → Outbound Call → Live Qualification → Objection Handling
          → Follow-up Email → Stripe Payment Link → Payment Confirmed
          → Memory Stored → Next call remembers everything
```

**Most AI sales tools stop at "book a meeting." Apex goes further.**

## Tech Stack

| Layer                   | Technology                                                         | Why                                                                                       |
| ----------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| **Outbound calling**    | [AgentPhone](https://agentphone.ai)                                | Provisions phone numbers for AI agents, handles inbound/outbound calls via webhook        |
| **Voice AI**            | [Gemini 2.0 Flash](https://ai.google.dev/gemini-api/docs/live-api) | Low-latency text generation; handles Maya's responses mid-call                            |
| **Real-time knowledge** | [Moss](https://usemoss.dev)                                        | <10ms semantic search over product FAQ — fires during the live call so Maya never pauses  |
| **Lead memory**         | [Supermemory](https://supermemory.ai)                              | Persistent memory graph; every call and email stored and recalled on the next interaction |
| **Follow-up email**     | [AgentMail](https://agentmail.to)                                  | AI agent inbox — sends personalized follow-up with the payment link                       |
| **Payment**             | [Stripe](https://stripe.com)                                       | Checkout Session created at call close, link sent via email, webhook confirms payment     |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    APEX BACKEND (FastAPI)                       │
│                                                                 │
│  Dashboard ──POST /api/start-campaign──▶ AgentPhone API         │
│                                              │                  │
│                                         Outbound call           │
│                                              │                  │
│  ┌───────────── Voice Turn Loop ────────────▼──────────────┐    │
│  │                                                         │    │
│  │  AgentPhone STT ──▶ POST /webhook/voice                 │    │
│  │                            │                            │    │
│  │              ┌─────────────┼──────────────┐             │    │
│  │              │             │              │             │    │
│  │           Moss          Supermemory    Gemini 2.0       │    │
│  │         (<10ms)          (recall)      Flash            │    │
│  │              │             │              │             │    │
│  │              └─────────────┴──────────────┘             │    │
│  │                            │                            │    │
│  │                    Streaming NDJSON                     │    │
│  │                   {"text": "...", "interim": true}      │    │
│  │                            │                            │    │
│  │                    AgentPhone TTS ──▶ Lead hears Maya   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  agent.call_ended webhook                                       │
│          │                                                      │
│          ├──▶ Supermemory.add(transcript)                       │
│          ├──▶ Stripe.checkout.Session.create($30)               │
│          └──▶ AgentMail.send(email + payment link)              │
│                                                                 │
│  /webhook/stripe ──payment_intent.succeeded──▶ Dashboard        │
└─────────────────────────────────────────────────────────────────┘
```

## Quickstart

### Prerequisites

- Python 3.11+
- Node.js 18+
- `ngrok` or `localtunnel` for webhook tunneling

### 1. Install

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your keys. All keys are pre-loaded for the hackathon demo.

The one key you must add yourself:

```bash
# Get free at https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_key_here
```

### 3. Expose a public tunnel

**Option A — ngrok (recommended, auto-detected by start.sh):**

```bash
# Add your authtoken first: https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_NEW_TOKEN
ngrok http 8000
```

**Option B — localtunnel (no signup required):**

```bash
npx localtunnel --port 8000 --subdomain apex-sdr
# → https://apex-sdr.loca.lt
# Note: if using localtunnel, set WEBHOOK_URL manually (step 4) — start.sh only auto-detects ngrok.
```

### 4. Set WEBHOOK_URL

```bash
# In .env:
WEBHOOK_URL=https://apex-sdr.loca.lt   # or your ngrok URL
```

### 5. Run

```bash
# Terminal 1
cd backend && python -m uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev

# Open: http://localhost:5173
```

Or use the one-command startup (requires ngrok):

```bash
chmod +x start.sh && ./start.sh
```

---

## Key Endpoints

| Endpoint                | Method    | Description                                |
| ----------------------- | --------- | ------------------------------------------ |
| `/api/start-campaign`   | POST      | Dials the lead via AgentPhone              |
| `/webhook/voice`        | POST      | AgentPhone sends each voice turn here      |
| `/webhook/stripe`       | POST      | Stripe payment confirmed                   |
| `/api/simulate-payment` | POST      | Demo backup — fires payment event manually |
| `/api/followup-call`    | POST      | Shows Supermemory recall for second call   |
| `/api/events`           | GET (SSE) | Live dashboard event stream                |
| `/health`               | GET       | Backend health + state                     |

---

## Project Structure

```
./                        # repo root (this directory)
├── backend/
│   ├── main.py           # FastAPI server — all routes
│   ├── voice_handler.py  # AgentPhone webhook + Gemini + streaming NDJSON
│   ├── moss_client.py    # Moss semantic search (+ keyword fallback)
│   ├── memory_client.py  # Supermemory store and recall
│   ├── stripe_client.py  # Stripe Checkout Session creation
│   ├── mail_client.py    # AgentMail follow-up email
│   ├── state.py          # Shared in-memory state + SSE queue
│   └── prompts.py        # Maya's system prompt and sales script
├── frontend/
│   └── src/App.jsx       # Mission control dashboard (React + Tailwind)
├── .env                  # API keys (gitignored)
├── .env.example          # Key names without values
├── requirements.txt
├── Makefile
└── start.sh              # One-command startup with ngrok auto-detection
```

---

## Built With

- [AgentPhone](https://agentphone.ai) — phone numbers and voice calls for AI agents
- [Google Gemini 2.0 Flash](https://ai.google.dev) — fast voice AI brain
- [Moss](https://usemoss.dev) — sub-10ms real-time semantic search
- [Supermemory](https://supermemory.ai) — persistent memory for AI agents
- [AgentMail](https://agentmail.to) — email for AI agents
- [Stripe](https://stripe.com) — payment infrastructure

---

_Apex · YC Call My Agent Hackathon · May 17, 2026_
