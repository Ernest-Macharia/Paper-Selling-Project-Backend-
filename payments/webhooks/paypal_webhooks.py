import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_paypal_event(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    invoice_number = resource.get("invoice_number")
    fallback_id = resource.get("id")

    payment = (
        Payment.objects.filter(external_id=fallback_id).first()
        or Payment.objects.filter(external_id=invoice_number).first()
    )

    if payment:
        PaymentEvent.objects.create(
            payment=payment, gateway="paypal", event_type=event_type, raw_data=payload
        )

    if event_type == "PAYMENT.SALE.COMPLETED" and payment:
        update_payment_status(invoice_number, "completed")

    return HttpResponse(status=200)
