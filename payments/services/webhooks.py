import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.webhooks.mpesa_webhooks import handle_mpesa_event
from payments.webhooks.paypal_webhooks import handle_paypal_event
from payments.webhooks.stripe_webhooks import handle_stripe_event


@csrf_exempt
def stripe_webhook(request):
    payload = json.loads(request.body)
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    handle_stripe_event(payload, sig_header)
    return HttpResponse(status=200)


@csrf_exempt
def paypal_webhook(request):
    payload = json.loads(request.body)
    print("Webhook payload received:", payload)

    handle_paypal_event(payload)
    return HttpResponse(status=200)


@csrf_exempt
def mpesa_webhook(request):
    payload = json.loads(request.body)
    handle_mpesa_event(payload)
    return HttpResponse(status=200)
