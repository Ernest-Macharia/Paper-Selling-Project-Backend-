import logging

import requests
from django.conf import settings

DEFAULT_TIMEOUT = 60
logger = logging.getLogger(__name__)


def get_paypal_access_token():
    """
    Get PayPal OAuth2 access token.
    Works for both sandbox and live environments.
    """
    api_url = (
        "https://api-m.paypal.com/v1/oauth2/token"
        if settings.PAYPAL_MODE == "live"
        else "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    )

    try:
        response = requests.post(
            api_url,
            auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json", "Accept-Language": "en_US"},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("PayPal API did not return an access token")
        return token

    except requests.exceptions.RequestException as e:
        logger.error(f"[PayPal] Failed to get access token: {e}")
        raise Exception("Failed to authenticate with PayPal API")
