import logging

import paypalrestsdk
import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


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


def verify_paypal_payment(payment_id, order):
    paypalrestsdk.configure(
        {
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET,
        }
    )

    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        logger.info(f"[PayPal] Payment {payment_id} status: {payment.state}")

        if payment.state == "approved":
            if order.status != "completed":
                order.status = "completed"
                order.save(update_fields=["status"])
            return True

        logger.warning(f"[PayPal] Payment not approved: {payment_id}")
        return False
    except paypalrestsdk.ResourceNotFound:
        logger.error(f"[PayPal] Payment not found: {payment_id}")
        return False
    except Exception as e:
        logger.exception(f"[PayPal] Error verifying payment {payment_id}: {str(e)}")
        return False
