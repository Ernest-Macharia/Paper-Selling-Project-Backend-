import logging

from django.conf import settings
from intasend import APIService

from payments.models import Payment

from .models import IntaSendPayment

logger = logging.getLogger(__name__)


def get_intasend_service():
    """Initialize IntaSend APIService only when called."""
    return APIService(
        publishable_key=settings.INTASEND_PUBLISHABLE_KEY,
        secret_key=settings.INTASEND_SECRET_KEY,
        test=settings.INTASEND_TEST_MODE,
    )


def handle_intasend_checkout(order):
    """Initiate IntaSend checkout session for an order."""
    if order.status == "completed":
        raise ValueError("Order has already been completed")

    try:
        user = order.user
        papers = order.papers.all()
        description = f"Purchase of {papers[0].title}" if papers else "Exam papers"

        success_url = f"{settings.BASE_URL}/payments/success/?order_id={order.id}"
        # cancel_url = f"{settings.BASE_URL}/payments/cancel/?order_id={order.id}"

        service = get_intasend_service()
        resp = service.collect.checkout(
            amount=float(order.price),
            currency="KES",
            email=user.email,
            first_name=getattr(user, "first_name", ""),
            last_name=getattr(user, "last_name", ""),
            phone_number=getattr(user, "phone", None),
            redirect_url=success_url,
        )

        checkout_url = resp.get("url")
        invoice_id = resp.get("invoice_id")

        payment = Payment.objects.create(
            gateway="intasend",
            external_id=invoice_id,
            amount=order.price,
            currency="KES",
            description=description,
            status="created",
            order=order,
            customer_email=user.email,
        )

        IntaSendPayment.objects.create(
            payment=payment,
            invoice_id=invoice_id,
            checkout_url=checkout_url,
            metadata=resp,
        )

        return {
            "checkout_url": checkout_url,
            "invoice_id": invoice_id,
            "public_key": settings.INTASEND_PUBLISHABLE_KEY,
        }

    except Exception:
        logger.exception("Error creating IntaSend checkout")
        raise
