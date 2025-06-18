import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


def process_stripe_refund(payment):
    try:
        refund = stripe.Refund.create(payment_intent=payment.stripe_session_id)
        return {"status": "success", "refund_id": refund.id}
    except stripe.error.StripeError as e:
        return {"status": "failed", "error": str(e)}
