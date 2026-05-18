import os
import sys
import json
import asyncio
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
import httpx
from dotenv import load_dotenv

# Load .env from apex/ directory
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

# Add backend dir to path for absolute imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import call_state, reset_state, emit_event
from voice_handler import handle_voice_turn, handle_call_ended
from moss_client import initialize_moss
from mail_client import initialize_inbox, send_booking_confirmation, send_post_class_feedback
import stripe as stripe_lib
stripe_lib.api_key = os.getenv("Stripe_secret_key")

app = FastAPI(title="Apex AI Receptionist Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AGENTPHONE_KEY = os.getenv("Agent_phone_key")
LEADS = [
    {"name": "Sarah K.", "phone": "+17143101206", "email": "quachphuwork@gmail.com"}
]

_apex_agent_id = None   # cached agent ID — created once, reused forever
_from_number   = None   # cached E.164 from-number — resolved once
_setup_done    = False  # True after first successful setup


@app.on_event("startup")
async def startup():
    call_state["sse_queue"] = asyncio.Queue()
    await initialize_moss()
    await initialize_inbox()
    _register_stripe_webhook()
    print("🚀 Apex backend ready")
    # Pre-warm AgentPhone in background — dial button will be instant
    asyncio.create_task(_ensure_agentphone_ready())


def _register_stripe_webhook():
    """Register /webhook/stripe with Stripe if not already registered."""
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url or not stripe_lib.api_key:
        return
    target = webhook_url.rstrip("/") + "/webhook/stripe"
    try:
        existing = stripe_lib.WebhookEndpoint.list(limit=20)
        for ep in existing.auto_paging_iter():
            if ep.url == target:
                print(f"✅ Stripe webhook already registered: {target}")
                return
        ep = stripe_lib.WebhookEndpoint.create(
            url=target,
            enabled_events=["checkout.session.completed", "payment_intent.succeeded"],
        )
        print(f"✅ Stripe webhook registered: {target}  (id={ep.id})")
    except Exception as e:
        print(f"⚠️  Stripe webhook registration skipped: {e}")


# ── SSE stream for dashboard ──────────────────────────────────────

@app.get("/api/events")
async def sse_stream(request: Request):
    async def event_generator():
        # Send current state immediately on connect
        yield {
            "data": json.dumps({
                "type": "state",
                "data": {
                    "status": call_state["status"],
                    "pipeline": call_state["pipeline"],
                    "transcript": call_state["transcript"],
                    "stripe_payment_url": call_state["stripe_payment_url"],
                    "memory_recall": call_state["memory_recall"],
                    "moss_queries": call_state["moss_queries"],
                }
            })
        }

        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(
                    call_state["sse_queue"].get(), timeout=25
                )
                yield {"data": json.dumps(event)}
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"type": "ping"})}

    return EventSourceResponse(event_generator())


# ── One-time AgentPhone setup (runs at startup, not on every dial) ────────────

async def _ensure_agentphone_ready():
    """
    Creates the Maya agent + attaches the phone number exactly ONCE.
    Subsequent calls just reuse _apex_agent_id and _from_number.
    """
    global _apex_agent_id, _from_number, _setup_done

    if _setup_done:
        return True   # already ready — skip all API calls

    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url or webhook_url == "https://your-ngrok-url.ngrok.io":
        return False

    webhook_endpoint = webhook_url.rstrip("/") + "/webhook/voice"
    headers = {
        "Authorization": f"Bearer {AGENTPHONE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=15.0)) as client:
            # 1 ─ Create agent (only once)
            if not _apex_agent_id:
                r = await client.post(
                    "https://api.agentphone.ai/v1/agents",
                    headers=headers,
                    json={
                        "name": "Maya — CoreFlow Pilates",
                        "voiceMode": "webhook",
                        "beginMessage": "Hi there! This is Maya calling from CoreFlow Pilates. Do you have just 60 seconds?",
                        "voice": "Polly.Joanna",
                        "sttMode": "accurate",
                        "ambientSound": "office",
                    }
                )
                if r.status_code not in (200, 201):
                    print(f"❌ Agent creation failed: {r.text[:200]}")
                    return False
                _apex_agent_id = r.json().get("id")
                print(f"✅ Agent created: {_apex_agent_id}")

            # 2 ─ Register webhook
            await client.post(
                "https://api.agentphone.ai/v1/webhooks",
                headers=headers,
                json={"url": webhook_endpoint, "contextLimit": 10}
            )

            # 3 ─ Resolve from-number (env override → dynamic lookup)
            env_num = os.getenv("AGENTPHONE_FROM_NUMBER", "").strip()
            number_id = None

            if env_num:
                nr = await client.get("https://api.agentphone.ai/v1/numbers", headers=headers)
                items = nr.json().get("data") or nr.json().get("items") or []
                matched = [n for n in items
                           if (n.get("phoneNumber") or n.get("phone_number") or
                               n.get("number") or n.get("e164")) == env_num]
                number_id   = matched[0].get("id") if matched else None
                _from_number = env_num
                print(f"📞 From-number: {_from_number}  id={number_id}")
            else:
                nr = await client.get("https://api.agentphone.ai/v1/numbers", headers=headers)
                items = nr.json().get("data") or nr.json().get("items") or []
                voice = [n for n in items
                         if n.get("type", "").lower() not in ("shared-imessage", "imessage", "sms")]
                if voice:
                    number_id    = voice[0].get("id")
                    _from_number = (voice[0].get("phoneNumber") or voice[0].get("phone_number")
                                    or voice[0].get("number") or voice[0].get("e164"))
                    print(f"📞 From-number (dynamic): {_from_number}  id={number_id}")
                else:
                    print("❌ No voice-capable numbers found")
                    return False

            # 4 ─ Attach number to agent
            if number_id:
                ar = await client.post(
                    f"https://api.agentphone.ai/v1/agents/{_apex_agent_id}/numbers",
                    headers=headers,
                    json={"numberId": number_id}
                )
                print(f"📎 Number attached → {ar.status_code}")
                await asyncio.sleep(1)   # let AgentPhone propagate

            _setup_done = True
            print("✅ AgentPhone setup complete — ready to dial instantly")
            return True

    except Exception as e:
        import traceback
        print(f"❌ AgentPhone setup error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


# ── Start campaign ────────────────────────────────────────────────

class LeadOverride(BaseModel):
    name: str
    phone: str
    email: str = ""

class StartCampaignBody(BaseModel):
    lead: LeadOverride | None = None

@app.post("/api/start-campaign")
async def start_campaign(body: StartCampaignBody = StartCampaignBody()):
    global _apex_agent_id, _from_number

    reset_state()
    call_state["sse_queue"] = asyncio.Queue()

    # Use lead from request if provided, otherwise fall back to hardcoded list
    if body.lead:
        lead = {"name": body.lead.name, "phone": body.lead.phone, "email": body.lead.email}
    else:
        lead = LEADS[0]
    call_state["lead"] = lead
    call_state["status"] = "calling"
    await emit_event("status_change", {"status": "calling", "lead": lead})

    webhook_url = os.getenv("WEBHOOK_URL", "")
    if not webhook_url or webhook_url == "https://your-ngrok-url.ngrok.io":
        call_state["status"] = "idle"
        return JSONResponse(status_code=400, content={
            "error": "WEBHOOK_URL not configured",
            "detail": "Set WEBHOOK_URL in .env to your ngrok/tunnel public URL."
        })

    # Ensure agent + number are set up (no-op after first call)
    ready = await _ensure_agentphone_ready()
    if not ready:
        call_state["status"] = "idle"
        return {"error": "AgentPhone setup failed — check API key and WEBHOOK_URL"}

    call_state["agent_id"] = _apex_agent_id

    headers = {
        "Authorization": f"Bearer {AGENTPHONE_KEY}",
        "Content-Type": "application/json"
    }

    if not _from_number:
        call_state["status"] = "idle"
        return {"error": "No from-number resolved — set AGENTPHONE_FROM_NUMBER in .env"}

    # ── Dial immediately (agent + number already set up) ─────────────
    call_payload = {
        "agentId": _apex_agent_id,
        "toNumber": lead["phone"],
        "initialGreeting": "Hi! This is Maya calling from CoreFlow Pilates. Is this a good moment for a quick 60-second chat?",
        "voice": "Polly.Joanna",
        "fromNumber": _from_number,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as client:
            call_resp = await client.post(
                "https://api.agentphone.ai/v1/calls",
                headers=headers,
                json=call_payload
            )
        print(f"📲 Initiate call → {call_resp.status_code}: {call_resp.text[:300]}")
    except Exception as e:
        call_state["status"] = "idle"
        return {"error": f"Call request failed: {e}"}

    if call_resp.status_code not in (200, 201):
        call_state["status"] = "idle"
        return {"error": "Failed to initiate call", "detail": call_resp.text}

    call_data = call_resp.json()
    call_id   = call_data.get("id")
    call_state["call_id"]  = call_id
    call_state["status"]   = "active"
    call_state["pipeline"]["call_connected"] = True

    await emit_event("pipeline_update", {"key": "call_connected", "value": True})
    await emit_event("status_change", {"status": "active"})

    return {"success": True, "call_id": call_id, "agent_id": _apex_agent_id}


# ── AgentPhone voice webhook ──────────────────────────────────────

@app.post("/webhook/voice")
async def voice_webhook(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(content={"ok": True})

    event = body.get("event")
    channel = body.get("channel")

    if event == "agent.message" and channel == "voice":
        # Extract transcript from AgentPhone payload
        data = body.get("data", {})
        caller_text = (
            data.get("transcript") or
            data.get("message") or
            body.get("message", {}).get("content", "") or
            ""
        ).strip()

        recent_history = body.get("recentHistory", [])

        if not caller_text:
            return StreamingResponse(
                iter([json.dumps({"text": ""}) + "\n"]),
                media_type="application/x-ndjson"
            )

        async def generate():
            async for chunk in handle_voice_turn(caller_text, recent_history):
                yield chunk

        return StreamingResponse(generate(), media_type="application/x-ndjson")

    elif event == "agent.call_ended":
        asyncio.create_task(handle_call_ended(
            call_id=body.get("callId") or body.get("data", {}).get("callId", ""),
            body=body
        ))
        return {"ok": True}

    return {"ok": True}


# ── Stripe webhook ────────────────────────────────────────────────

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        return {"ok": True}

    event_type = payload.get("type", "")

    if event_type in ("checkout.session.completed", "payment_intent.succeeded"):
        obj = payload.get("data", {}).get("object", {})
        amount = obj.get("amount_total") or obj.get("amount_received") or 100
        customer_email = obj.get("customer_email") or obj.get("receipt_email") or "quachphuwork@gmail.com"

        call_state["pipeline"]["stripe_paid"] = True
        await emit_event("pipeline_update", {"key": "stripe_paid", "value": True})
        await emit_event("stripe_paid", {
            "amount": amount / 100,
            "currency": "usd",
            "customer": call_state["lead"]["name"] if call_state.get("lead") else "Sarah K."
        })

        # Fire booking confirmation email immediately
        asyncio.create_task(send_booking_confirmation(customer_email))

    return {"ok": True}


# ── Stripe success redirect (fires when user completes payment) ───
# Stripe redirects to WEBHOOK_URL/stripe-success?session_id=... after checkout.
# This fires the pipeline event and sends the user back to the dashboard.

@app.get("/stripe-success")
async def stripe_success(session_id: str = ""):
    """Called by Stripe success_url redirect — no webhook registration needed."""
    lead_name  = call_state["lead"]["name"]  if call_state.get("lead") else "Sarah K."
    lead_email = call_state["lead"]["email"] if call_state.get("lead") else "quachphuwork@gmail.com"

    if not call_state["pipeline"].get("stripe_paid"):
        call_state["pipeline"]["stripe_paid"] = True
        await emit_event("pipeline_update", {"key": "stripe_paid", "value": True})
        await emit_event("stripe_paid", {
            "amount": 1.00,
            "currency": "usd",
            "customer": lead_name,
        })
        asyncio.create_task(send_booking_confirmation(lead_email))
        print(f"✅ Stripe payment confirmed via success redirect — session {session_id}")

    # Redirect back to the dashboard
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    return RedirectResponse(url=frontend_url)


# ── Simulate payment (demo backup) ───────────────────────────────

@app.post("/api/simulate-payment")
async def simulate_payment():
    """Dashboard button backup — fires payment success event manually."""
    call_state["pipeline"]["stripe_paid"] = True
    await emit_event("pipeline_update", {"key": "stripe_paid", "value": True})
    await emit_event("stripe_paid", {
        "amount": 30.00,
        "currency": "usd",
        "customer": call_state["lead"]["name"] if call_state.get("lead") else "Sarah K."
    })
    # Also fire booking confirmation email
    asyncio.create_task(send_booking_confirmation("quachphuwork@gmail.com"))
    return {"ok": True, "message": "Payment simulated"}


# ── Follow-up call (shows Supermemory recall) ─────────────────────

@app.post("/api/followup-call")
async def followup_call():
    from memory_client import recall_lead
    lead = LEADS[0]
    memory = await recall_lead(lead["phone"])

    if not memory:
        memory = (
            "Sarah K. called on May 17, 2026 regarding CoreFlow Pilates beginner trial. "
            "Qualified: True. Interested in Saturday 10 AM class. Expressed interest but "
            "had cost objection — resolved with risk-free trial offer. Payment link sent."
        )

    call_state["memory_recall"] = memory
    await emit_event("memory_recall", {"content": memory})
    await emit_event("status_change", {"status": "followup_active"})
    return {"memory": memory}


# ── Post-class feedback email (demo button) ────────────────────────

@app.post("/api/send-feedback")
async def send_feedback():
    """Sends Sofia's post-class instructor feedback email — demo button."""
    lead = LEADS[0]
    success = await send_post_class_feedback(lead["email"], lead["name"])
    await emit_event("email_sent", {
        "to": lead["email"],
        "type": "post_class_feedback",
        "subject": "Sofia's feedback from your first CoreFlow class",
    })
    return {"ok": success}


# ── Health check ──────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "call_status": call_state["status"],
        "moss_queries": len(call_state["moss_queries"]),
        "transcript_turns": len(call_state["transcript"]),
        "pipeline": call_state["pipeline"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
