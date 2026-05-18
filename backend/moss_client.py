import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

try:
    from moss import MossClient, DocumentInfo, QueryOptions
    MOSS_AVAILABLE = True
except ImportError:
    MOSS_AVAILABLE = False
    print("⚠️  Moss SDK not installed — will use keyword fallback")

MOSS_DOCS = [
    {
        "id": "beginner-mat-class",
        "text": "Beginner Mat Pilates at CoreFlow is a 60-minute floor-based class using only a mat. No prior experience or equipment needed. Sofia guides you through breathing, core activation, spinal articulation, and foundational movements. Class size is private (one-on-one with the instructor). Perfect for complete beginners or anyone returning after a long break. Available Saturday 10:00 AM and Tuesday 6:00 PM. $1 trial deposit, fully refundable."
    },
    {
        "id": "intermediate-reformer-class",
        "text": "Intermediate Reformer Pilates uses the reformer machine with adjustable spring resistance to deepen core work and build full-body strength. Recommended for clients who have completed at least 3-5 mat sessions. Classes are small group (max 4 people). Available Thursday 7:00 PM. Included with the $150/month membership — first session is free with any monthly plan."
    },
    {
        "id": "full-schedule",
        "text": "CoreFlow Pilates class schedule: Saturday 10:00 AM — Beginner Mat (4 spots total, booking open). Tuesday 6:00 PM — Beginner Mat (6 spots total, booking open). Thursday 7:00 PM — Intermediate Reformer (6 spots total, currently on waitlist). All classes are 60 minutes. Booking must be made at least 24 hours in advance. Call or email to reserve your spot."
    },
    {
        "id": "pricing-complete",
        "text": "CoreFlow Pilates pricing: Trial class $1 (60 minutes, private, fully refundable). Monthly unlimited mat membership $120/month. Monthly unlimited mat + reformer membership $150/month, includes first reformer session free. Drop-in rate after trial: $45 per class. No contracts — cancel monthly membership anytime with 7 days notice. Trial deposit is 100% refundable if you don't love it."
    },
    {
        "id": "what-to-expect-first-class",
        "text": "For your first session at CoreFlow: Arrive 10 minutes early. Sofia will do a 5-minute intake to understand your fitness background and any injuries or limitations. Then 50 minutes of guided movement. Wear comfortable, form-fitting workout clothes — leggings and a fitted top work well. Grip socks are required on the reformer (available at studio for $5). Bring water. Most beginners feel their core the next morning."
    },
    {
        "id": "pilates-vs-yoga",
        "text": "Pilates and yoga are both mind-body practices but work differently. Pilates focuses specifically on core strength, spinal alignment, postural correction, and controlled resistance movement — it uses equipment (reformer) or mat-based precise exercises. Yoga emphasizes flexibility, breath, and mindfulness. Pilates targets deep stabilizer muscles (transverse abdominis, multifidus) that yoga rarely isolates. About 40% of CoreFlow members also do yoga and say pilates gives them a stronger foundation for their yoga practice. Most clients see measurable core strength improvement within 3-4 pilates sessions."
    },
    {
        "id": "pilates-for-beginners",
        "text": "CoreFlow is specifically designed to be beginner-friendly. You do not need any prior pilates, yoga, or fitness experience. Sofia teaches every movement from scratch — nothing is assumed. The beginner mat class moves at a comfortable pace with modifications available for every exercise. Our most common new client is someone who has never worked out consistently and wants to start with something sustainable and low-impact."
    },
    {
        "id": "instructor-sofia",
        "text": "Sofia Rivera is CoreFlow's lead instructor. She has been teaching pilates for 8 years and holds a full certification through the Pilates Method Alliance (PMA) — the gold standard for pilates certification, requiring 450+ hours of training and passing a national exam. Sofia specializes in beginners, postpartum clients, and athletes using pilates for cross-training. She currently teaches all beginner mat and reformer classes at CoreFlow."
    },
    {
        "id": "location-parking",
        "text": "CoreFlow Pilates is at 123 Main Street, Santa Monica, CA 90401. Free parking is available in the lot behind the building, accessible from 2nd Street. The studio is 5 minutes walking from the Santa Monica Pier and 3 minutes from the Expo Line Downtown Santa Monica metro station. Street parking is also available on Main Street with 2-hour meters."
    },
    {
        "id": "cancellation-policy",
        "text": "Cancellation policy at CoreFlow: Cancel 24 or more hours before class for a full refund or free reschedule. Same-day cancellations receive no refund but may reschedule once without charge. Monthly memberships can be paused for up to 30 days per year at no cost. To cancel a monthly membership, give 7 days written notice — no cancellation fees. Trial class deposit is fully refundable if you don't love your first session."
    },
    {
        "id": "objection-price",
        "text": "The $1 trial at CoreFlow is essentially free — it's a zero-risk way to experience a completely private 60-minute session with a certified instructor. Unlike a yoga drop-in at $35-42, you pay just $1 and get one-on-one attention the whole time. The deposit is 100% refundable if you don't love it. Most members say the $1 trial was the best fitness decision they made that year."
    },
    {
        "id": "objection-time",
        "text": "CoreFlow's Saturday 10 AM class is designed for people with busy weekday schedules. It runs exactly 60 minutes with no commute pressure — park behind the building, walk in, done by 11 AM. Tuesday 6 PM is the most popular weeknight option. Many members book Saturday for consistency. Sofia is flexible with rescheduling if something comes up — just give 24 hours notice."
    },
    {
        "id": "health-injuries",
        "text": "Sofia has experience working with clients managing lower back pain, knee issues, hip tightness, shoulder problems, and post-surgery recovery. Pilates is low-impact and highly modifiable — every exercise can be adjusted for your body. Sofia does a brief intake before your first session to understand any limitations and modify the workout accordingly. CoreFlow is not a medical facility and cannot diagnose or treat conditions — always consult your doctor for serious medical concerns before starting any exercise program."
    },
    {
        "id": "online-booking",
        "text": "To book a trial class at CoreFlow Pilates: You can reserve online at coreflowpilates.com, reply to this email with your preferred date, or call us at (310) 555-0100. Payment of $1 secures your spot. Saturday 10 AM currently has availability. Once booked, you will receive a confirmation email with the studio address, parking instructions, what to bring, and Sofia's contact information."
    },
]

INDEX_NAME = "coreflow-pilates"
_moss_client = None
_index_loaded = False


def _keyword_fallback(question: str) -> str:
    """Map keywords to the best matching MOSS_DOCS entry by ID."""
    q = question.lower()
    _idx = {d["id"]: d["text"] for d in MOSS_DOCS}

    if any(w in q for w in ["expensive", "afford", "too much", "worth", "risk"]):
        return _idx["objection-price"]
    if any(w in q for w in ["busy", "time", "schedule", "when", "saturday", "tuesday", "thursday",
                             "sunday", "monday", "wednesday", "friday", "weekend", "today",
                             "available", "slot", "other class", "other session", "any other",
                             "day", "days", "pm", "am", "morning", "evening", "afternoon"]):
        return _idx["full-schedule"]
    if any(w in q for w in ["price", "cost", "dollar", "$", "how much", "fee", "drop-in", "membership"]):
        return _idx["pricing-complete"]
    if any(w in q for w in ["yoga", "different", "difference", "versus", "vs", "compare", "gym", "crossfit"]):
        return _idx["pilates-vs-yoga"]
    if any(w in q for w in ["cancel", "refund", "policy", "reschedule", "contract", "commitment"]):
        return _idx["cancellation-policy"]
    if any(w in q for w in ["beginner", "never", "first time", "experience", "new to", "start"]):
        return _idx["pilates-for-beginners"]
    if any(w in q for w in ["location", "where", "address", "parking", "santa monica", "directions"]):
        return _idx["location-parking"]
    if any(w in q for w in ["instructor", "teacher", "certified", "sofia", "qualified"]):
        return _idx["instructor-sofia"]
    if any(w in q for w in ["back", "knee", "injury", "hurt", "pain", "safe", "modify", "recovery", "surgery"]):
        return _idx["health-injuries"]
    if any(w in q for w in ["wear", "bring", "prepare", "expect", "first class", "arrival", "how long"]):
        return _idx["what-to-expect-first-class"]
    if any(w in q for w in ["book", "reserve", "online", "website"]):
        return _idx["online-booking"]
    return _idx["pricing-complete"]


async def initialize_moss():
    global _moss_client, _index_loaded
    if not MOSS_AVAILABLE:
        print("⚠️  Moss unavailable — using keyword fallback for FAQ queries")
        return

    project_id = os.getenv("MOSS_PROJECT_ID")
    project_key = os.getenv("MOSS_PROJECT_KEY")

    if not project_id or not project_key:
        print("⚠️  MOSS_PROJECT_ID/KEY not set — using keyword fallback")
        return

    try:
        _moss_client = MossClient(project_id, project_key)
        docs = [DocumentInfo(id=d["id"], text=d["text"]) for d in MOSS_DOCS]

        # Try to load existing index first, create if it doesn't exist
        try:
            await _moss_client.load_index(INDEX_NAME)
            _index_loaded = True
            print(f"✅ Moss index '{INDEX_NAME}' loaded from cloud")
        except Exception:
            print(f"Creating Moss index '{INDEX_NAME}'...")
            await _moss_client.create_index(INDEX_NAME, docs, "moss-minilm")
            await _moss_client.load_index(INDEX_NAME)
            _index_loaded = True
            print(f"✅ Moss index created and loaded ({len(docs)} documents)")
    except Exception as e:
        print(f"⚠️  Moss init failed: {e} — using keyword fallback")
        _index_loaded = False


async def query_moss(question: str) -> dict:
    """Returns {"result": str, "latency_ms": int}"""
    start = time.time()

    if not _index_loaded or _moss_client is None:
        result = _keyword_fallback(question)
        latency = int((time.time() - start) * 1000)
        return {"result": result, "latency_ms": latency}

    try:
        results = await _moss_client.query(INDEX_NAME, question, QueryOptions(top_k=2, alpha=0.7))
        latency = int((time.time() - start) * 1000)
        result_text = results.docs[0].text if results.docs else _keyword_fallback(question)
        return {"result": result_text, "latency_ms": latency}
    except Exception as e:
        print(f"Moss query error: {e}")
        latency = int((time.time() - start) * 1000)
        return {"result": _keyword_fallback(question), "latency_ms": latency}
