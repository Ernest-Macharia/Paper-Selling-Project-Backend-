import json
import logging

import requests
from django.conf import settings

from paypal_api.utils import get_paypal_access_token

DEFAULT_TIMEOUT = 60
logger = logging.getLogger(__name__)


def verify_paypal_signature(request):
    """
    Verify PayPal webhook signature to ensure the request is authentic.

    Args:
        request: Django HttpRequest object containing the webhook payload

    Returns:
        bool: True if signature is valid, False otherwise
    """
    try:
        headers = request.headers
        body = request.body.decode("utf-8")

        # Required headers for verification
        required_headers = [
            "PAYPAL-TRANSMISSION-ID",
            "PAYPAL-TRANSMISSION-TIME",
            "PAYPAL-CERT-URL",
            "PAYPAL-AUTH-ALGO",
            "PAYPAL-TRANSMISSION-SIG",
        ]

        # Check if all required headers are present
        if not all(header in headers for header in required_headers):
            logger.error("Missing required PayPal webhook headers")
            return False

        # Parse the JSON body if it's a string
        try:
            webhook_event = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            logger.error("Invalid JSON payload in PayPal webhook")
            return False

        verification_data = {
            "transmission_id": headers["PAYPAL-TRANSMISSION-ID"],
            "transmission_time": headers["PAYPAL-TRANSMISSION-TIME"],
            "cert_url": headers["PAYPAL-CERT-URL"],
            "auth_algo": headers["PAYPAL-AUTH-ALGO"],
            "transmission_sig": headers["PAYPAL-TRANSMISSION-SIG"],
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": webhook_event,
        }

        api_url = (
            "https://api-m.paypal.com/v1/notifications/verify-webhook-signature"
            if settings.PAYPAL_MODE == "live"
            else "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"
        )

        response = requests.post(
            api_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {get_paypal_access_token()}",
            },
            json=verification_data,
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code != 200:
            logger.error(
                f"PayPal verification failed with status {response.status_code}: {response.text}"
            )
            return False

        verification_status = response.json().get("verification_status")
        if verification_status != "SUCCESS":
            logger.error(f"PayPal verification failed: {verification_status}")
            return False

        return True

    except Exception as e:
        logger.exception(f"Error verifying PayPal signature: {e}")
        return False
