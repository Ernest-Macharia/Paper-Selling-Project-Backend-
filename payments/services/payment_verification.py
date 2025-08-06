import logging

import requests
import stripe
from django.conf import settings

from paypal_api.checkout import get_paypal_access_token
from paypal_api.models import PayPalPayment
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

    paypal_payment = PayPalPayment.objects.filter(
        payment__order=order, paypal_order_id=session_id
    ).first()

    if not paypal_payment:
        logger.error(
            f"[PayPal] No PayPalPayment found for\
            order {order.id} with session_id/token {session_id}"
        )
        return False

    payment_id = paypal_payment.paypal_order_id
    response = requests.get(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{payment_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=DEFAULT_TIMEOUT,
    )

    if response.status_code != 200:
        logger.error(f"[PayPal] Could not fetch order {payment_id}: {response.text}")
        return False

    order_data = response.json()
    logger.info(f"[PayPal] Order data: {order_data}")

    if order_data["status"] == "COMPLETED":
        order.status = "completed"
        order.save(update_fields=["status"])
        paypal_payment.payment.status = "completed"
        paypal_payment.payment.save(update_fields=["status"])
        return True

    logger.warning(f"[PayPal] Order {payment_id} status is not COMPLETED")
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
