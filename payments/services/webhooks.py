import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.utils.paypal_verification import verify_paypal_signature
from payments.webhooks.mpesa_webhooks import handle_mpesa_event
from payments.webhooks.paypal_webhooks import handle_paypal_event
from payments.webhooks.stripe_webhooks import handle_stripe_event

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    return handle_stripe_event(request)


@csrf_exempt
def paypal_webhook(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    if not verify_paypal_signature(payload):
        return HttpResponse("Invalid signature", status=400)

    try:
        return handle_paypal_event(request)
    except Exception as e:
        logger.exception("[PayPal Webhook] Unexpected error: %s", e)
        return HttpResponse(status=500)


@csrf_exempt
def mpesa_webhook(request):
    payload = json.loads(request.body)
    handle_mpesa_event(payload)
    return HttpResponse(status=200)
