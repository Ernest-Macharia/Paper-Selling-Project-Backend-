# payments/webhooks/mpesa_webhooks.py

import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status


@csrf_exempt
def handle_mpesa_event(request):
    payload = json.loads(request.body)
    stk = payload.get("Body", {}).get("stkCallback", {})
    checkout_request_id = stk.get("CheckoutRequestID")
    result_code = stk.get("ResultCode")

    payment = Payment.objects.filter(external_id=checkout_request_id).first()

    PaymentEvent.objects.create(
        payment=payment, gateway="mpesa", event_type="stkCallback", raw_data=payload
    )

    if result_code == 0 and payment:
        update_payment_status(checkout_request_id, "completed")

    return HttpResponse(status=200)
