import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')

import stripe

stripe.api_key = os.getenv("Stripe_secret_key")


def create_payment_link(
    customer_email: str,
    amount_cents: int = 100,
    description: str = "CoreFlow Pilates — Beginner Trial Class"
) -> str:
    """Creates a Stripe Checkout Session and returns the payment URL.

    Uses success_url = WEBHOOK_URL/stripe-success so the backend receives the
    payment confirmation directly via redirect — no Stripe webhook registration required.
    """
    if not stripe.api_key:
        print("⚠️  Stripe key not set — returning demo URL")
        return "https://buy.stripe.com/test_demo_link"

    webhook_url  = os.getenv("WEBHOOK_URL", "").rstrip("/")
    success_url  = (
        f"{webhook_url}/stripe-success?session_id={{CHECKOUT_SESSION_ID}}"
        if webhook_url
        else "http://localhost:5173"
    )
    cancel_url   = os.getenv("FRONTEND_URL", "http://localhost:5173")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {
                        "name": description,
                        "description": "60-minute beginner session · Saturday 10:00 AM · Sofia Rivera",
                        "images": [],
                    },
                },
                "quantity": 1,
            }],
            mode="payment",
            customer_email=customer_email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "source": "apex_ai_sdr",
                "lead_email": customer_email,
            }
        )
        print(f"✅ Stripe Checkout Session created: {session.id}")
        print(f"   success_url → {success_url}")
        return session.url
    except Exception as e:
        print(f"❌ Stripe error: {e}")
        return "https://buy.stripe.com/test_demo_link"
