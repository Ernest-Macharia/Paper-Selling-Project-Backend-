import logging
import uuid

import requests
import stripe
from django.conf import settings

from paypal_api.utils import get_paypal_access_token
from pesapal.checkout import get_pesapal_auth_token

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


def verify_stripe_payment(session_id, order):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            order.status = "completed"
            order.save(update_fields=["status"])
            return True
    except Exception as e:
        logger.exception("Error during payment verification: %s", e)
    return False


def verify_paypal_payment(session_id, order):
    access_token = get_paypal_access_token()
    logger.info(f"[PayPal] Verifying session_id: {session_id} for order: {order.id}")

    try:
        capture_url = (
            f"https://api.sandbox.paypal.com/v2/checkout/orders/{session_id}/capture"
            if settings.PAYPAL_MODE != "live"
            else f"https://api.paypal.com/v2/checkout/orders/{session_id}/capture"
        )

        # Ensure headers include Content-Type and Authorization
        headers = {
            "Content-Type": "application/json",  # Required for POST requests
            "Authorization": f"Bearer {access_token}",
            "PayPal-Request-Id": str(uuid.uuid4()),  # Helps track requests
        }

        # Use json=None to ensure no body is sent
        capture_response = requests.post(
            capture_url,
            headers=headers,
            json=None,  # Explicitly send no body
            timeout=DEFAULT_TIMEOUT,
        )

        if capture_response.status_code != 201:
            logger.error(
                f"[PayPal] Capture failed (HTTP {capture_response.status_code}): {capture_response.text}"
            )
            return False

        capture_data = capture_response.json()
        logger.info(f"[PayPal] Capture data: {capture_data}")

        if capture_data.get("status") == "COMPLETED":
            # ... rest of your success handling logic ...
            return True

    except Exception as e:
        logger.exception(f"[PayPal] Error during verification: {e}")

    return False


def verify_paystack_payment(reference, order):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            f"{settings.PAYSTACK_API_URL}/transaction/verify/{reference}",
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code != 200:
            logger.error(f"Paystack verification error: {response.text}")
            return False

        data = response.json()
        if data["data"]["status"] == "success":
            order.status = "completed"
            order.save(update_fields=["status"])
            return True

    except Exception as e:
        logger.exception("Error during Paystack payment verification: %s", e)

    return False


def verify_pesapal_payment(order_tracking_id, order):
    auth_token = get_pesapal_auth_token()

    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        # Check payment status
        status_url = (
            f"{settings.PESAPAL_API_BASE}/api/Transactions/GetTransactionStatus"
        )
        params = {"orderTrackingId": order_tracking_id}

        response = requests.get(
            status_url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()

        status_data = response.json()

        if status_data.get("payment_status") == "COMPLETED":
            order.status = "completed"
            order.save(update_fields=["status"])
            return True

    except Exception as e:
        logger.exception(f"Error verifying Pesapal payment: {e}")

    return False
