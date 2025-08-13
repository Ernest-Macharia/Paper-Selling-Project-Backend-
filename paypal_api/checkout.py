import logging

import requests
from django.conf import settings

from payments.models import Payment
from paypal_api.models import PayPalPayment
from paypal_api.utils import get_paypal_access_token

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


def handle_paypal_checkout(order):
    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

    access_token = get_paypal_access_token()

    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {
                    "currency_code": "USD",
                    "value": f"{order.price:.2f}",
                },
                "description": f"Purchase of {first_paper.title}",
            }
        ],
        "application_context": {
            "return_url": settings.PAYPAL_SUCCESS_URL.replace(
                "{ORDER_ID}", str(order.id)
            ),
            "cancel_url": settings.PAYPAL_CANCEL_URL.replace(
                "{ORDER_ID}", str(order.id)
            ),
        },
    }

    response = requests.post(
        (
            "https://api.paypal.com/v2/checkout/orders"
            if settings.PAYPAL_MODE == "live"
            else "https://api.sandbox.paypal.com/v2/checkout/orders"
        ),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "Prefer": "return=representation",
        },
        json=data,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    approval_url = next(
        (link["href"] for link in result["links"] if link["rel"] == "approve"), None
    )
    if not approval_url:
        raise Exception("Approval URL not found in PayPal response")

    payment = Payment.objects.create(
        gateway="paypal",
        external_id=result["id"],
        amount=order.price,
        currency="USD",
        description=f"Purchase of {first_paper.title}",
        status="created",
        order=order,
        customer_email=order.user.email,
    )

    created = PayPalPayment.objects.get_or_create(
        payment=payment, defaults={"paypal_order_id": result["id"], "status": "created"}
    )
    if not created:
        logger.warning(f"PayPalPayment already existed for order {order.id}")

    return {
        "checkout_url": approval_url,
        "order_id": order.id,
        "session_id": result["id"],
    }
