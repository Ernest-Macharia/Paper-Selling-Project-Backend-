import logging

import stripe
from django.conf import settings

from payments.models import Payment
from stripe_api.models import StripePayment

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


def handle_stripe_checkout(order):
    if order.status == "completed":
        raise ValueError("Order has already been completed")

    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

    try:
        amount_cents = int(order.price * 100)
        baseURL = settings.BASE_URL

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": first_paper.title,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            metadata={
                "order_id": str(order.id),
                "paper_id": str(first_paper.id),
                "user_id": str(order.user.id),
            },
            expand=["payment_intent"],
            idempotency_key=f"order-{order.id}",
            success_url=f"{baseURL}/payment/success?session_id]\
                ={{CHECKOUT_SESSION_ID}}&order_id={order.id}",
            cancel_url=settings.STRIPE_CANCEL_URL,
        )

        # Create Payment record
        payment = Payment.objects.create(
            gateway="stripe",
            external_id=session.id,
            amount=order.price,
            currency="USD",
            description=f"Purchase of {first_paper.title}",
            status="created",
            order=order,
            customer_email=order.user.email,
        )

        # Store Stripe-specific metadata
        StripePayment.objects.create(
            payment=payment,
            session_id=session.id,
            payment_intent=session.payment_intent,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "public_key": settings.STRIPE_PUBLISHABLE_KEY,
        }

    except Exception:
        logger.exception("Error during Stripe checkout session creation")
        raise
