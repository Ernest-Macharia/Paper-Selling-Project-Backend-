import logging

from django.conf import settings
from intasend import APIService

from payments.models import Payment

logger = logging.getLogger(__name__)


def get_intasend_service():
    """Initialize IntaSend APIService only when called."""
    return APIService(
        publishable_key=settings.INTASEND_PUBLISHABLE_KEY,
        secret_key=settings.INTASEND_SECRET_KEY,
        test=settings.INTASEND_TEST_MODE,
    )


def verify_intasend_payment(invoice_id, order):
    """Check IntaSend payment status."""
    try:
        service = get_intasend_service()
        resp = service.collect.status(invoice_id=invoice_id)
        state = resp.get("state")

        payment = Payment.objects.get(external_id=invoice_id, order=order)

        if state == "COMPLETE":
            payment.status = "completed"
            order.status = "completed"
            payment.save()
            order.save()
            return True
        elif state == "FAILED":
            payment.status = "failed"
            payment.save()
            return False
        else:
            payment.status = "pending"
            payment.save()
            return False
    except Payment.DoesNotExist:
        logger.error(f"Payment not found for invoice_id {invoice_id}")
        return False
    except Exception:
        logger.exception("Error verifying IntaSend payment")
        return False
