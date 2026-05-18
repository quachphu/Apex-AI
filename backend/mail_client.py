import os
from pathlib import Path
from dotenv import load_dotenv
from state import emit_event

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

try:
    import agentmail
    from agentmail import AgentMail
    AGENTMAIL_AVAILABLE = True
except ImportError:
    AGENTMAIL_AVAILABLE = False
    print("⚠️  AgentMail SDK not installed")

_client = None
_inbox_id = None


def get_client():
    global _client
    if _client is None and AGENTMAIL_AVAILABLE:
        api_key = os.getenv("Agent_mail_S25")
        if api_key:
            _client = AgentMail(api_key=api_key)
    return _client


async def initialize_inbox():
    global _inbox_id
    client = get_client()
    if client is None:
        print("⚠️  AgentMail not available")
        return

    try:
        response = client.inboxes.list()
        # ListInboxesResponse has .inboxes attribute
        inbox_list = getattr(response, 'inboxes', None) or []

        if inbox_list and len(inbox_list) > 0:
            _inbox_id = inbox_list[0].inbox_id
            email = getattr(inbox_list[0], 'email', _inbox_id)
            print(f"✅ AgentMail inbox ready: {email}")
        else:
            from agentmail.inboxes.types import CreateInboxRequest
            inbox = client.inboxes.create(
                request=CreateInboxRequest(
                    username="apex-maya",
                    display_name="Maya from CoreFlow Pilates"
                )
            )
            _inbox_id = inbox.inbox_id
            email = getattr(inbox, 'email', _inbox_id)
            print(f"✅ AgentMail inbox created: {email}")
    except Exception as e:
        print(f"AgentMail init error: {e}")
        _inbox_id = None


async def send_followup(
    to_email: str,
    lead_name: str,
    payment_url: str,
    call_summary: str = ""
) -> bool:
    client = get_client()
    if client is None:
        print("⚠️  AgentMail not available — skipping email")
        return False

    if not _inbox_id:
        await initialize_inbox()

    if not _inbox_id:
        print("⚠️  No AgentMail inbox available")
        return False

    first_name = lead_name.split()[0] if lead_name else "there"

    body = f"""Hi {first_name},

It was so great speaking with you just now! I'm thrilled to have you try CoreFlow Pilates.

As promised, here's your payment link to lock in your Saturday 10 AM beginner session:

👉  {payment_url}

It takes about 30 seconds to complete. Once you're booked, you'll get a confirmation with our address and what to wear.

Can't wait to see you Saturday!

Warmly,
Maya
CoreFlow Pilates Studio
📍 123 Main Street, Santa Monica, CA 90401
📞 (310) 555-0100
"""

    try:
        client.inboxes.messages.send(
            inbox_id=_inbox_id,
            to=[to_email],
            subject="Your CoreFlow Pilates Trial — Saturday 10 AM",
            text=body,
        )
        print(f"✅ AgentMail: follow-up sent to {to_email}")
        return True
    except Exception as e:
        print(f"AgentMail send error: {e}")
        return False


async def send_booking_confirmation(to_email: str) -> bool:
    """Fires immediately after Stripe payment — confirms booking with full class details."""
    client = get_client()
    if client is None:
        print("⚠️  AgentMail not available — skipping booking confirmation")
        return False

    if not _inbox_id:
        await initialize_inbox()

    if not _inbox_id:
        print("⚠️  No AgentMail inbox — skipping booking confirmation")
        return False

    body = """Hi Sarah,

Your spot is confirmed! Here are your class details:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅  Saturday, May 18, 2026
⏰  10:00 AM – 11:00 AM
📍  CoreFlow Pilates
    123 Main Street
    Santa Monica, CA 90401
    (Free parking behind building off 2nd St)
👩‍🏫  Instructor: Sofia Rivera
🧘  Class: Beginner Mat Pilates (60 min, private)
💳  Paid: $1.00 ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What to bring:
- Comfortable workout clothes (leggings + fitted top)
- Water bottle
- Arrive 10 minutes early for your intake with Sofia

Sofia's note to new clients:
"Don't worry about knowing anything beforehand — I'll guide you through every movement. Just bring an open mind and comfortable clothes. I'm excited to meet you!"

Questions? Reply to this email or call (310) 555-0100.

See you Saturday!

Maya & the CoreFlow team
CoreFlow Pilates · 123 Main St, Santa Monica CA
(310) 555-0100 · coreflowpilates.com
"""

    try:
        client.inboxes.messages.send(
            inbox_id=_inbox_id,
            to=[to_email],
            subject="✅ Confirmed: CoreFlow Pilates — Saturday 10 AM",
            text=body,
        )
        print(f"✅ AgentMail: booking confirmation sent to {to_email}")
        await emit_event("email_sent", {
            "to": to_email,
            "type": "booking_confirmation",
            "subject": "✅ Confirmed: CoreFlow Pilates — Saturday 10 AM",
        })
        return True
    except Exception as e:
        print(f"Booking confirmation email error: {e}")
        return False


async def send_post_class_feedback(to_email: str, lead_name: str) -> bool:
    """Instructor feedback email — sent after class completion (demo button)."""
    client = get_client()
    if client is None:
        print("⚠️  AgentMail not available — skipping feedback email")
        return False

    if not _inbox_id:
        await initialize_inbox()

    if not _inbox_id:
        print("⚠️  No AgentMail inbox — skipping feedback email")
        return False

    first_name = lead_name.split()[0] if lead_name else "there"

    body = f"""Hi {first_name},

Sofia wanted to personally follow up after your first session at CoreFlow Pilates yesterday. We loved having you!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 SOFIA'S FEEDBACK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What went really well:
✓ Strong natural core awareness — you picked up the breathing pattern quickly
✓ Great focus and willingness to try every movement
✓ Excellent control during the Roll-Up sequence

Focus area for your next session:
→ Hip flexor release during the Hundred exercise
   Sofia noticed a slight tendency to hike the right hip — very common
   for people who sit at a desk. This will open up naturally with practice.

Sofia's homework for you (5 minutes daily):
- 3x cat-cow stretches in the morning to wake up the spine
- 1-minute supine hip flexor stretch each side before bed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sofia's personal note:

"{first_name} showed real natural body awareness for a first session.
The hip alignment will click within 2-3 more classes.
I'd love to see them back for Tuesday 6 PM or the next Saturday."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ready for your next session?

Tuesday 6:00 PM — Beginner Mat (2 spots available)
Saturday 10:00 AM — Beginner Mat (3 spots available)

Reply to this email or visit coreflowpilates.com/book to reserve.

Your second class is just $45 — or switch to our monthly unlimited
membership for $120/month and never think about booking again.

Looking forward to continuing your pilates journey!

Sofia Rivera & the CoreFlow team
CoreFlow Pilates · 123 Main St, Santa Monica CA
(310) 555-0100 · coreflowpilates.com
"""

    try:
        client.inboxes.messages.send(
            inbox_id=_inbox_id,
            to=[to_email],
            subject=f"Sofia's feedback from your first CoreFlow class 🧘",
            text=body,
        )
        print(f"✅ AgentMail: post-class feedback sent to {to_email}")
        return True
    except Exception as e:
        print(f"Post-class feedback email error: {e}")
        return False
