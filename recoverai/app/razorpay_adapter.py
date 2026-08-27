"""
Razorpay sandbox adapter.

Keeps recovery/policy logic completely decoupled from the payment provider
(section 23 of the blueprint). If RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET are
set as env vars, this calls the real Razorpay test-mode API. If they are
NOT set, it falls back to a clearly-labeled mock mode -- so the recovery
loop, policy engine, and dashboard all keep working end-to-end for a demo
even without live sandbox credentials.

Verify current Razorpay API capabilities against their docs before
production use: https://razorpay.com/docs/api/payments/payment-links/
"""
import os
import uuid
import time

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

_client = None
_LIVE_MODE = False

if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        import razorpay
        _client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
        _LIVE_MODE = True
    except ImportError:
        _client = None
        _LIVE_MODE = False


def is_live_mode() -> bool:
    return _LIVE_MODE


def create_payment_link(amount_rupees: float, customer_id: str, case_id: str, description: str = "") -> dict:
    """
    Create a test-mode Razorpay payment link, or a mock one if no
    sandbox credentials are configured. Returns a normalized dict
    regardless of mode so callers never need to branch on it.
    """
    if _LIVE_MODE:
        try:
            link = _client.payment_link.create({
                "amount": int(amount_rupees * 100),  # paise
                "currency": "INR",
                "description": description or f"Recovery for case {case_id}",
                "notes": {"case_id": case_id, "customer_id": customer_id},
                "notify": {"sms": False, "email": False},  # sandbox: no real outreach
            })
            return {
                "mode": "live_sandbox",
                "payment_link_id": link.get("id"),
                "short_url": link.get("short_url"),
                "status": link.get("status", "created"),
            }
        except Exception as e:
            return {"mode": "live_sandbox_error", "error": str(e)}

    # Mock mode -- clearly labeled, deterministic shape, safe for demo
    return {
        "mode": "mock",
        "payment_link_id": f"plink_mock_{uuid.uuid4().hex[:12]}",
        "short_url": f"https://rzp.io/mock/{uuid.uuid4().hex[:8]}",
        "status": "created",
    }


def check_payment_status(payment_link_id: str) -> dict:
    """Check the status of a previously created payment link."""
    if _LIVE_MODE and not payment_link_id.startswith("plink_mock_"):
        try:
            link = _client.payment_link.fetch(payment_link_id)
            return {"mode": "live_sandbox", "status": link.get("status")}
        except Exception as e:
            return {"mode": "live_sandbox_error", "error": str(e)}

    return {"mode": "mock", "status": "unknown", "note": "mock link -- verify via /recovery/verify instead"}