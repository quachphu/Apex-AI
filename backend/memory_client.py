import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

try:
    from supermemory import Supermemory
    SUPERMEMORY_AVAILABLE = True
except ImportError:
    SUPERMEMORY_AVAILABLE = False
    print("⚠️  Supermemory SDK not installed")

_client = None


def get_client():
    global _client
    if _client is None and SUPERMEMORY_AVAILABLE:
        api_key = os.getenv("SUPERMEMORY_API_KEY")
        if api_key:
            _client = Supermemory(api_key=api_key)
    return _client


async def store_call(phone: str, name: str, transcript: list, qualified: bool, notes: str = "") -> bool:
    client = get_client()
    if client is None:
        print("⚠️  Supermemory not available — skipping memory storage")
        return False

    transcript_text = "\n".join([
        f"{t['role'].upper()}: {t['text']}" for t in transcript
    ])
    content = f"""Call with {name} ({phone}) — CoreFlow Pilates Sales Call
Qualified: {qualified}
Notes: {notes}

TRANSCRIPT:
{transcript_text}
"""
    # Supermemory container tags must be alphanumeric + hyphens/underscores only
    safe_tag = phone.replace("+", "").replace(" ", "-").replace("(", "").replace(")", "")
    try:
        client.add(
            content=content,
            container_tags=[safe_tag],
            metadata={"name": name, "qualified": str(qualified), "source": "apex_call"}
        )
        print(f"✅ Supermemory: stored call for {name} ({phone})")
        return True
    except Exception as e:
        print(f"Supermemory store error: {e}")
        return False


async def recall_lead(phone: str) -> str:
    client = get_client()
    if client is None:
        return ""

    safe_tag = phone.replace("+", "").replace(" ", "-").replace("(", "").replace(")", "")
    try:
        profile = client.profile(container_tag=safe_tag)
        parts = []
        if hasattr(profile, 'profile'):
            p = profile.profile
            if hasattr(p, 'static') and p.static:
                parts.append(str(p.static))
            if hasattr(p, 'dynamic') and p.dynamic:
                parts.append(str(p.dynamic))
        return "\n".join(parts).strip()
    except Exception as e:
        print(f"Supermemory recall error: {e}")
        # Try search as fallback
        try:
            results = client.search.documents(
                q="CoreFlow Pilates call",
                container_tags=[safe_tag]
            )
            if results and hasattr(results, 'results') and results.results:
                return results.results[0].content[:500]
        except Exception:
            pass
        return ""
