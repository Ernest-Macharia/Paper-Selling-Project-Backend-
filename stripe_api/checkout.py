import stripe
from django.conf import settings

from payments.models import Payment
from stripe_api.models import StripePayment

stripe.api_key = settings.STRIPE_SECRET_KEY


def handle_stripe_checkout(data):
    amount_cents = int(data["amount"] * 100)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": data["currency"].lower(),
                    "product_data": {
                        "name": data.get("description", "Order"),
                    },
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        customer_email=data.get("email", None),
    )

    # Create unified payment record
    payment = Payment.objects.create(
        gateway="stripe",
        external_id=session.id,
        amount=data["amount"],
        currency=data["currency"],
        customer_email=data.get("email"),
        description=data.get("description"),
        status="created",
    )

    StripePayment.objects.create(
        payment=payment, session_id=session.id, payment_intent=session.payment_intent
    )

    return {"checkout_url": session.url, "session_id": session.id}
