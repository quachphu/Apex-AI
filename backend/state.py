import asyncio

call_state = {
    "status": "idle",           # idle | calling | active | ended
    "lead": None,               # current lead dict
    "transcript": [],           # list of {"role": "agent"|"lead", "text": str}
    "moss_queries": [],         # list of {"query": str, "result": str, "latency_ms": int}
    "pipeline": {
        "call_connected": False,
        "objection_handled": False,
        "email_sent": False,
        "stripe_paid": False,
        "memory_saved": False,
    },
    "memory_recall": None,      # Supermemory recall on 2nd call
    "stripe_payment_url": None,
    "call_id": None,
    "agent_id": None,
    "sse_queue": None,          # asyncio.Queue for SSE events
    # Conversation state machine
    "conversation_stage": "INTRO",   # INTRO → QUALIFY → PITCH → CLOSE → CONFIRMED → DECLINED
    "turn_count": 0,
    "has_closed": False,
    "call_complete": False,          # True when [CALL_COMPLETE] detected — stop processing
    "objection_count": 0,
}


def infer_stage(transcript: list, has_closed: bool) -> str:
    """Infer conversation stage from transcript history and content signals."""
    if has_closed:
        return "CONFIRMED"

    turn_count = len(transcript)
    if turn_count == 0:
        return "INTRO"

    # Look at the full conversation text so far
    full_text = " ".join(t["text"].lower() for t in transcript)
    agent_turns = [t for t in transcript if t["role"] == "agent"]

    # CLOSE: agent has already pitched and asked for the payment/booking
    close_keywords = ["send you a payment link", "send a quick payment link",
                      "lock in that saturday", "lock in your saturday",
                      "send the link", "payment link to your email"]
    if any(kw in full_text for kw in close_keywords):
        return "CLOSE"

    # PITCH: agent has mentioned the $1 trial or made an offer
    pitch_keywords = ["$1", "one dollar", "beginner trial", "private session",
                      "saturday 10", "saturday at 10", "60-minute", "60 minute"]
    if any(kw in full_text for kw in pitch_keywords) and len(agent_turns) >= 1:
        return "PITCH"

    # QUALIFY: at least one exchange has happened
    if turn_count >= 2:
        return "QUALIFY"

    # Still on first lead utterance — stay in QUALIFY (not CLOSE)
    return "QUALIFY"


async def emit_event(event_type: str, data: dict):
    """Push an SSE event onto the dashboard queue."""
    queue = call_state.get("sse_queue")
    if queue:
        await queue.put({"type": event_type, "data": data})


def reset_state():
    call_state["status"] = "idle"
    call_state["lead"] = None
    call_state["transcript"] = []
    call_state["moss_queries"] = []
    call_state["pipeline"] = {k: False for k in call_state["pipeline"]}
    call_state["memory_recall"] = None
    call_state["stripe_payment_url"] = None
    call_state["call_id"] = None
    call_state["agent_id"] = None
    call_state["conversation_stage"] = "INTRO"
    call_state["turn_count"] = 0
    call_state["has_closed"] = False
    call_state["call_complete"] = False
    call_state["objection_count"] = 0
