import requests
from django.conf import settings

DEFAULT_TIMEOUT = 60


def verify_paypal_signature(request):
    headers = request.headers
    body = request.body.decode("utf-8")

    verification_data = {
        "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID"),
        "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME"),
        "cert_url": headers.get("PAYPAL-CERT-URL"),
        "auth_algo": headers.get("PAYPAL-AUTH-ALGO"),
        "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG"),
        "webhook_id": settings.PAYPAL_WEBHOOK_ID,
        "webhook_event": body,
    }

    response = requests.post(
        (
            "https://api-m.paypal.com/v1/notifications/verify-webhook-signature"
            if settings.PAYPAL_MODE == "live"
            else "https://api-m.sandbox.paypal.com/v1/notifications/"
            "verify-webhook-signature"
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_paypal_access_token()}",
        },
        json=verification_data,
        timeout=DEFAULT_TIMEOUT,
    )

    try:
        return (
            response.status_code == 200
            and response.json().get("verification_status") == "SUCCESS"
        )
    except Exception:
        return False


def get_paypal_access_token():
    resp = requests.post(
        (
            "https://api-m.paypal.com/v1/oauth2/token"
            if settings.PAYPAL_MODE == "live"
            else "https://api-m.sandbox.paypal.com/v1/oauth2/token"
        ),
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        data={"grant_type": "client_credentials"},
        timeout=DEFAULT_TIMEOUT,
    )
    return resp.json()["access_token"]
