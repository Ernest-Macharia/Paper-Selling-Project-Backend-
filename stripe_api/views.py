import stripe
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from payments.models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
@require_POST
def create_stripe_session(request):
    import json

    data = json.loads(request.body)

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": data["title"],
                    },
                    "unit_amount": int(float(data["amount"]) * 100),  # convert to cents
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
    )

    return JsonResponse({"id": session.id})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        Payment.objects.update_or_create(
            external_id=session["id"],
            defaults={
                "gateway": "stripe",
                "amount": session["amount_total"] / 100,
                "status": "completed",
                "currency": session["currency"].upper(),
                "customer_email": session["customer_email"],
                "description": "Stripe payment",
            },
        )

    return HttpResponse(status=200)


def stripe_payment_success(request):
    return HttpResponse(
        "<h1>✅ Payment was successful!</h1><p>Thank you for your purchase.</p>"
    )


def stripe_payment_cancelled(request):
    return HttpResponse(
        "<h1>❌ Payment was cancelled.</h1><p>You can try again at any time.</p>"
    )
