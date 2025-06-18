import stripe
from django.conf import settings

from payments.models import Payment
from stripe_api.models import StripePayment

stripe.api_key = settings.STRIPE_SECRET_KEY


def handle_stripe_checkout(order):
    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

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
        },
        success_url=f"{baseURL}/api/exampapers/papers/{first_paper.id}/download/",
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

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

    StripePayment.objects.create(
        payment=payment,
        session_id=session.id,
        payment_intent=session.payment_intent,
    )

    return {"checkout_url": session.url, "session_id": session.id}
