import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status


@csrf_exempt
def handle_paypal_event(request):
    payload = json.loads(request.body)
    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    invoice_number = resource.get("invoice_number")

    payment = Payment.objects.filter(external_id=invoice_number).first()

    PaymentEvent.objects.create(
        payment=payment, gateway="paypal", event_type=event_type, raw_data=payload
    )

    if event_type == "PAYMENT.SALE.COMPLETED" and payment:
        update_payment_status(invoice_number, "completed")

    return HttpResponse(status=200)
