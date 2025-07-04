import json

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.utils.paypal_verification import verify_paypal_signature
from payments.webhooks.mpesa_webhooks import handle_mpesa_event
from payments.webhooks.paypal_webhooks import handle_paypal_event
from payments.webhooks.stripe_webhooks import handle_stripe_event


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret,
        )
        handle_stripe_event(event)
        return HttpResponse(status=200)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)
    except Exception:
        return HttpResponse(status=500)


@csrf_exempt
def paypal_webhook(request):
    payload = json.loads(request.body)

    if not verify_paypal_signature(payload):
        return HttpResponse("Invalid signature", status=400)

    try:
        return handle_paypal_event(payload)
    except Exception:
        return HttpResponse(status=500)


@csrf_exempt
def mpesa_webhook(request):
    payload = json.loads(request.body)
    handle_mpesa_event(payload)
    return HttpResponse(status=200)
