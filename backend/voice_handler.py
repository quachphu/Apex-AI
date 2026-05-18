import os
import json
import asyncio
import random
from typing import AsyncGenerator
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

try:
    from google import genai
    from google.genai import types as genai_types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️  google-genai not installed")

from state import call_state, infer_stage, emit_event
from moss_client import query_moss
from memory_client import recall_lead, store_call
from prompts import MAYA_SYSTEM_PROMPT
from stripe_client import create_payment_link
from mail_client import send_followup

_gemini_client = None


def get_gemini_client():
    global _gemini_client
    if _gemini_client is None and GEMINI_AVAILABLE:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


# ─────────────────────────────────────────────────────────────────────────────
# MOSS TRIGGER KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────

MOSS_TRIGGERS = [
    # Pricing
    "price", "cost", "how much", "dollar", "$", "expensive", "worth",
    "afford", "cheap", "fee", "charge", "refund", "money", "pay",
    # Schedule / availability
    "schedule", "when", "saturday", "sunday", "monday", "tuesday",
    "wednesday", "thursday", "friday", "weekend", "time", "today",
    "available", "availability", "slot", "book", "appointment", "open",
    "spot", "class", "session", "day",
    # Location
    "where", "location", "address", "parking", "drive", "far",
    "santa monica", "get there", "directions",
    # Pilates explanation / comparison
    "what is pilates", "pilates", "yoga", "different", "difference",
    "versus", "vs", "compare", "better", "similar", "crossfit",
    "gym", "workout", "exercise", "fitness",
    # Beginner questions
    "beginner", "never", "first time", "experience", "know how",
    "never tried", "new to", "start", "learn",
    # Instructor
    "instructor", "teacher", "trainer", "who", "certified",
    "qualified", "sofia", "background",
    # Cancellation / policy
    "cancel", "refund", "policy", "change", "reschedule", "miss",
    "contract", "commitment", "lock in",
    # Health / injury
    "back", "knee", "injury", "hurt", "pain", "safe", "modify",
    "pregnant", "recovery", "surgery", "health",
    # What to expect
    "wear", "bring", "prepare", "expect", "first class", "what happens",
    "arrival", "how long",
]

# Clearly off-topic/garbled — skip Moss for these
IGNORE_PATTERNS = [
    "pirate", "computer", "coding", "software", "engineer",
    "are you a robot", "are you ai", "are you human", "are you real",
    "what are you", "who made you", "artificial intelligence",
]


def should_query_moss(text: str) -> bool:
    text_lower = text.lower()
    if any(pattern in text_lower for pattern in IGNORE_PATTERNS):
        return False
    return any(trigger in text_lower for trigger in MOSS_TRIGGERS)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _is_garbled(text: str) -> bool:
    """Return True when STT input is too short, empty, or full of repeated words."""
    cleaned = text.strip()
    words = cleaned.split()
    if not cleaned or len(cleaned) < 2:
        return True
    if cleaned.lower() in {"um", "uh", "hmm", "hm", "", "yeah", "yep", "ok", "okay", "mhm"}:
        return True
    if len(words) <= 2 and len(cleaned) < 5:
        return True
    # Detect heavy repetition (garbled STT artefact)
    if len(words) > 2 and len(set(words)) < len(words) * 0.4:
        return True
    return False


def _classify_question(text: str) -> str:
    """Classify the lead's utterance so the fallback gives a topic-specific answer."""
    t = text.lower()
    # "Any other class / schedule / session / time / day / option" → show all classes
    if any(p in t for p in ["other class", "other session", "other schedule",
                             "other time", "other day", "other option",
                             "any others", "do you have any", "what else",
                             "what other", "different time", "different day"]):
        return "schedule_show_all"
    if any(d in t for d in ["sunday", "monday", "wednesday", "friday",
                             "weekend", "today", "tonight", "tomorrow"]):
        return "schedule_unavailable"
    # "two days" / "2 days" is often STT mishearing "Tuesday"
    if any(d in t for d in ["saturday", "tuesday", "thursday",
                             "two day", "2 day", "tues", "thurs"]):
        return "schedule_available"
    if ("what is pilates" in t or ("what" in t and "pilates" in t)
            or "never heard" in t or "explain" in t):
        return "explain_pilates"
    if any(w in t for w in ["how much", "price", "cost", "expensive", "fee",
                             "dollar", "pay", "charge", "worth", "affordable"]):
        return "pricing"
    if any(w in t for w in ["where", "location", "address", "parking",
                             "far", "drive", "santa monica", "directions"]):
        return "location"
    if any(w in t for w in ["instructor", "trainer", "teacher", "sofia",
                             "who teaches", "who is", "certified", "qualified"]):
        return "instructor"
    if any(w in t for w in ["beginner", "never tried", "first time", "new to",
                             "no experience", "never done", "just starting"]):
        return "beginner"
    if any(w in t for w in ["cancel", "refund", "policy", "reschedule",
                             "commitment", "lock in", "contract"]):
        return "cancellation"
    STRONG_YES = ["yes please", "sounds good", "let's do it", "i'll take it",
                  "sign me up", "book it", "go ahead", "do it", "i'm in", "perfect"]
    SOFT_YES   = ["yes", "yeah", "sure", "okay", "ok", "alright", "yep", "for sure"]
    if any(w in t for w in STRONG_YES + SOFT_YES):
        return "affirmation"
    if any(w in t for w in ["no", "not interested", "maybe later", "too busy",
                             "not now", "nope", "not really"]):
        return "decline"
    return "general"


def _fallback_response(caller_text: str, moss_context: str, current_stage: str) -> str:
    """Topic-aware fallback for when Gemini is unavailable."""
    if moss_context:
        # Use the full Moss text (trimmed to ~2 sentences) so schedule/FAQ answers are complete
        sentences = [s.strip() for s in moss_context.split('.') if s.strip()]
        summary = '. '.join(sentences[:3]) + '.'
        return f"{summary} Does Saturday morning at 10 AM work for you?"

    q = _classify_question(caller_text)

    if q == "schedule_show_all":
        return ("Sure! We have three class times: Saturday at 10 AM — Beginner Mat, "
                "Tuesday at 6 PM — Beginner Mat, and Thursday at 7 PM — Intermediate Reformer. "
                "The beginner trial works for Saturday or Tuesday. Which one sounds better for you?")

    if q == "schedule_unavailable":
        return ("We don't have classes on that day — our beginner openings are "
                "Saturday at 10 AM and Tuesday at 6 PM. Saturday tends to fill up fast! "
                "Does either of those work for you?")

    if q == "explain_pilates":
        return ("Pilates is a low-impact workout focused on core strength, posture, and "
                "controlled movement — think strength training meets flexibility. "
                "Our $1 trial is the best way to actually feel the difference. "
                "Would Saturday morning at 10 AM work for you?")

    if q == "pricing":
        return ("The beginner trial is just $1 — a private 60-minute one-on-one session "
                "with our certified instructor Sofia, fully refundable if you don't love it. "
                "Monthly membership after is $150 for unlimited classes. Does Saturday 10 AM work?")

    if q == "location":
        return ("We're at 123 Main Street in Santa Monica — right near the pier, "
                "free parking on site. Does Saturday morning at 10 AM work for you?")

    if q == "instructor":
        return ("Sofia Rivera teaches all our beginner sessions — Pilates Method Alliance "
                "certified, 8 years of experience, specialises in beginners. "
                "Want me to lock in Saturday 10 AM so you can meet her?")

    if q == "beginner":
        return ("Perfect — Sofia designed this trial specifically for beginners. "
                "No experience needed, and it's a private session so there's zero pressure. "
                "Would Saturday at 10 AM work for your first class?")

    if q == "cancellation":
        return ("No lock-in at all — 24-hour notice gets a full refund, and the $1 trial "
                "itself is 100% refundable if you don't love it. Zero risk. "
                "Does Saturday morning work?")

    if q == "affirmation":
        if current_stage in ("CLOSE", "CONFIRMED"):
            return ("Perfect! Sending that payment link to your email right now. "
                    "Looking forward to seeing you Saturday! [CALL_COMPLETE]")
        elif current_stage == "PITCH":
            return ("Wonderful! I'd love to lock in that Saturday 10 AM spot for you. "
                    "Can I send a quick payment link to your email? Takes about 30 seconds.")
        else:
            return ("That's great! We have a really popular beginner trial — just $1 for a "
                    "private 60-minute session with instructor Sofia. "
                    "Would Saturday morning at 10 AM work for you?")

    if q == "decline":
        return ("Totally understand — no pressure at all! "
                "Can I send you some info by email for when the timing's better?")

    stage_defaults = {
        "INTRO":     "Have you ever tried pilates before, or would this be your first time?",
        "QUALIFY":   ("We have a really popular beginner trial — just $1 for a private "
                      "session with instructor Sofia. Does Saturday 10 AM work?"),
        "PITCH":     ("Is there anything else you'd like to know before I lock in that "
                      "Saturday spot for you?"),
        "CLOSE":     ("Can I send you a quick payment link? It locks in your Saturday "
                      "10 AM spot in under 30 seconds."),
        "CONFIRMED": "You're all set! Check your email for the payment link. See you Saturday!",
        "DECLINED":  "No problem — I'll send some info over. Have a wonderful day!",
    }
    return stage_defaults.get(current_stage, "Sorry about that — can you say that again?")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN VOICE TURN HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def handle_voice_turn(caller_text: str, recent_history: list) -> AsyncGenerator[bytes, None]:
    """
    Called by AgentPhone webhook on every voice turn.
    Yields NDJSON chunks for streaming TTS.
    Pattern: garble-check → interim filler → Moss/memory → Gemini → final chunk.
    """

    # GUARD 1: Hard stop — call already fully complete
    if call_state.get("call_complete", False):
        yield (json.dumps({"text": "You're all set! Have a great day!"}) + "\n").encode()
        return

    # GUARD 2: Already closed — wrap up and lock down
    if call_state.get("has_closed", False):
        yield (json.dumps({"text": "You're all set — check your email and we'll see you Saturday! Bye!"}) + "\n").encode()
        call_state["call_complete"] = True
        return

    # GUARD 3: Garbled / nonsensical STT input
    if _is_garbled(caller_text):
        yield (json.dumps({"text": "Sorry, you broke up there — are you still with me?"}) + "\n").encode()
        return

    # ── Record lead turn ──────────────────────────────────────────────────────
    call_state["turn_count"] = call_state.get("turn_count", 0) + 1
    call_state["transcript"].append({"role": "lead", "text": caller_text})
    await emit_event("transcript", {"role": "lead", "text": caller_text})

    # ── Interim filler (prevents dead silence on turns 3+) ───────────────────
    if call_state["turn_count"] > 2:
        filler = random.choice([
            "Let me check that for you.",
            "Great question.",
            "Sure!",
            "Absolutely.",
        ])
        yield (json.dumps({"text": filler, "interim": True}) + "\n").encode()

    # ── Moss query ────────────────────────────────────────────────────────────
    moss_context = ""
    if should_query_moss(caller_text):
        moss_result = await query_moss(caller_text)
        moss_context = moss_result["result"]
        call_state["moss_queries"].append({
            "query": caller_text[:60],
            "result": moss_context[:120],
            "latency_ms": moss_result["latency_ms"],
        })
        await emit_event("moss_query", {
            "query": caller_text[:60],
            "result": moss_context[:120],
            "latency_ms": moss_result["latency_ms"],
        })
        call_state["pipeline"]["objection_handled"] = True
        await emit_event("pipeline_update", {"key": "objection_handled", "value": True})
        call_state["objection_count"] = call_state.get("objection_count", 0) + 1

    # ── Supermemory recall — fetch ONCE per session, then cache ───────────────
    memory_context = call_state.get("memory_recall") or ""
    if not memory_context and call_state.get("lead") and call_state["turn_count"] == 1:
        memory_context = await recall_lead(call_state["lead"]["phone"])
        if memory_context:
            call_state["memory_recall"] = memory_context
            await emit_event("memory_recall", {"content": memory_context})

    # ── Determine current stage ───────────────────────────────────────────────
    current_stage = infer_stage(call_state["transcript"], call_state.get("has_closed", False))

    # ── Build system prompt with stage injected ───────────────────────────────
    system_with_stage = MAYA_SYSTEM_PROMPT.format(
        current_stage=current_stage,
        turn_count=call_state["turn_count"],
        has_closed=call_state.get("has_closed", False),
    )

    if moss_context:
        system_with_stage += (
            f"\n\nPRODUCT KNOWLEDGE — use ALL of this to answer the lead's question, "
            f"then ask if Saturday 10 AM works:\n{moss_context}"
        )
    if memory_context:
        # Only pass clean conversational history — strip metadata/source tags
        safe_memory = memory_context
        for junk in ("apex_call", "source:", "metadata:", "containerTag", "qualified:"):
            safe_memory = safe_memory.replace(junk, "")
        safe_memory = safe_memory.strip()
        if safe_memory:
            system_with_stage += (
                f"\n\nNOTE — you spoke with this lead before. Here is the summary:\n"
                f"{safe_memory[:400]}"
            )

    # ── Build Gemini conversation history ─────────────────────────────────────
    # Exclude the turn we just appended (it becomes the final "user" message)
    contents = []
    for turn in call_state["transcript"][:-1]:
        role = "model" if turn["role"] == "agent" else "user"
        contents.append(
            genai_types.Content(
                role=role,
                parts=[genai_types.Part(text=turn["text"])]
            )
        ) if GEMINI_AVAILABLE else None

    # ── Call Gemini ───────────────────────────────────────────────────────────
    agent_text = ""
    gemini_client = get_gemini_client()

    if gemini_client and GEMINI_AVAILABLE:
        contents.append(
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=caller_text)]
            )
        )
        # Use run_in_executor to call the SYNC generate_content — this guarantees
        # the full response is collected before returning (aio variant streams chunks).
        for model_name in ("gemini-2.5-flash", "gemini-1.5-flash"):
            try:
                _contents  = list(contents)          # snapshot for lambda closure
                _system    = system_with_stage
                _model     = model_name
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: gemini_client.models.generate_content(
                        model=_model,
                        contents=_contents,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=_system,
                            max_output_tokens=256,
                            temperature=0.65,
                        )
                    )
                )
                # Collect full text — response.text may be None on safety blocks
                raw = ""
                if response and response.text:
                    raw = response.text
                elif response and response.candidates:
                    for cand in response.candidates:
                        if cand.content and cand.content.parts:
                            raw = "".join(
                                p.text for p in cand.content.parts if hasattr(p, "text") and p.text
                            )
                            if raw:
                                break
                agent_text = (raw
                              .replace("*", "").replace("#", "").replace("_", "")
                              .strip())
                if agent_text:
                    print(f"✅ Gemini ({model_name}): '{agent_text}'")
                    break
                else:
                    finish = (response.candidates[0].finish_reason
                              if response and response.candidates else "unknown")
                    print(f"⚠️  Gemini ({model_name}) empty — finish_reason={finish}")
                    break
            except Exception as e:
                print(f"❌ Gemini ({model_name}) error: {e}")
                agent_text = ""
                continue

    if not agent_text:
        agent_text = _fallback_response(caller_text, moss_context, current_stage)

    # ── Detect [CALL_COMPLETE] token ──────────────────────────────────────────
    if "[CALL_COMPLETE]" in agent_text:
        agent_text = agent_text.replace("[CALL_COMPLETE]", "").strip()
        call_state["has_closed"] = True
        call_state["call_complete"] = True
        asyncio.create_task(trigger_post_call_pipeline())

    # ── Detect close signals even without explicit token ─────────────────────
    # Require at least 4 turns (agent intro + lead answer + pitch + lead yes)
    # to prevent premature pipeline firing on early casual "yeah / for sure" replies.
    close_signals = [
        "sending that to your email",
        "sending the link",
        "you'll get the link",
        "you're all set",
        "check your email",
    ]
    min_turns_to_close = 4
    if (
        call_state["turn_count"] >= min_turns_to_close
        and any(sig in agent_text.lower() for sig in close_signals)
        and not call_state.get("has_closed")
    ):
        call_state["has_closed"] = True
        asyncio.create_task(trigger_post_call_pipeline())

    # ── Record agent turn and emit ────────────────────────────────────────────
    call_state["transcript"].append({"role": "agent", "text": agent_text})
    await emit_event("transcript", {"role": "agent", "text": agent_text})

    # ── Stream final response to AgentPhone TTS ───────────────────────────────
    yield (json.dumps({"text": agent_text}) + "\n").encode()


# ─────────────────────────────────────────────────────────────────────────────
# POST-CALL PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

async def trigger_post_call_pipeline():
    """Fires after Maya's closing line — non-blocking background task."""
    await asyncio.sleep(1.5)  # Let TTS finish speaking

    lead = call_state.get("lead")
    if not lead:
        return

    # Stripe payment link
    payment_url = create_payment_link(
        customer_email=lead["email"],
        amount_cents=100,
        description="CoreFlow Pilates — Beginner Trial Class (Sat 10 AM)"
    )
    call_state["stripe_payment_url"] = payment_url

    # Send follow-up email via AgentMail
    success = await send_followup(
        to_email=lead["email"],
        lead_name=lead["name"],
        payment_url=payment_url,
    )

    if success:
        call_state["pipeline"]["email_sent"] = True
        await emit_event("pipeline_update", {"key": "email_sent", "value": True})
        await emit_event("email_sent", {
            "to": lead["email"],
            "payment_url": payment_url,
        })


# ─────────────────────────────────────────────────────────────────────────────
# CALL ENDED HANDLER
# ─────────────────────────────────────────────────────────────────────────────

async def handle_call_ended(call_id: str, body: dict):
    """Called by AgentPhone agent.call_ended webhook."""
    lead = call_state.get("lead")
    if not lead:
        return

    qualified = call_state["pipeline"]["email_sent"]
    stored = await store_call(
        phone=lead["phone"],
        name=lead["name"],
        transcript=call_state["transcript"],
        qualified=qualified,
        notes="Trial class: Saturday 10 AM. Deposit: $1. Studio: CoreFlow Pilates."
    )

    if stored:
        call_state["pipeline"]["memory_saved"] = True
        await emit_event("pipeline_update", {"key": "memory_saved", "value": True})

    call_state["status"] = "ended"
    duration = body.get("data", {}).get("durationSeconds", 0)
    await emit_event("call_ended", {"duration": duration})
