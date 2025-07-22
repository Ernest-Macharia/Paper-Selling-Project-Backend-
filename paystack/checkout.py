# paystack_api/checkout.py
import logging

import requests
from django.conf import settings

from payments.models import Payment
from paystack.models import PaystackPayment

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60

PAYSTACK_API_URL = "https://api.paystack.co"


def handle_paystack_checkout(order):
    if order.status == "completed":
        raise ValueError("Order has already been completed")

    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

    try:
        amount_kobo = int(order.price * 100)  # Paystack uses kobo (1 NGN = 100 kobo)
        success_url = settings.PAYSTACK_SUCCESS_URL.replace("{ORDER_ID}", str(order.id))
        # cancel_url = settings.PAYSTACK_CANCEL_URL.replace("{ORDER_ID}", str(order.id))

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "email": order.user.email,
            "amount": amount_kobo,
            "currency": "USD",  # Or "USD" if you're charging in dollars
            "reference": f"ORDER_{order.id}_{order.user.id}",
            "callback_url": success_url,
            "metadata": {
                "order_id": str(order.id),
                "paper_id": str(first_paper.id),
                "user_id": str(order.user.id),
            },
        }

        response = requests.post(
            f"{PAYSTACK_API_URL}/transaction/initialize",
            headers=headers,
            json=payload,
            timeout=DEFAULT_TIMEOUT,
        )

        if response.status_code != 200:
            logger.error(f"Paystack API error: {response.text}")
            raise ValueError("Failed to initialize Paystack payment")

        data = response.json()
        reference = data["data"]["reference"]
        access_code = data["data"]["access_code"]
        authorization_url = data["data"]["authorization_url"]

        # Create Payment record
        payment = Payment.objects.create(
            gateway="paystack",
            external_id=reference,
            amount=order.price,
            currency="USD",  # Or "USD"
            description=f"Purchase of {first_paper.title}",
            status="created",
            order=order,
            customer_email=order.user.email,
        )

        # Store Paystack-specific info
        PaystackPayment.objects.create(
            payment=payment,
            reference=reference,
            access_code=access_code,
            authorization_url=authorization_url,
        )

        return {
            "checkout_url": authorization_url,
            "reference": reference,
            "public_key": settings.PAYSTACK_PUBLIC_KEY,
        }

    except Exception:
        logger.exception("Error during Paystack checkout initialization")
        raise
