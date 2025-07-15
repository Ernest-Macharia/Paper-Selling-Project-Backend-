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
    except json.JSONDecodeError as e:
        logger.error("[PayPal Webhook] JSON decode error: %s", e)
        return HttpResponse("Invalid JSON", status=400)

    event_type = payload.get("event_type")
    resource = payload.get("resource", {})
    invoice_number = resource.get("invoice_number")
    fallback_id = resource.get("id")

    logger.info(f"[PayPal Webhook] Received event: {event_type}")

    payment = (
        Payment.objects.filter(external_id=fallback_id).first()
        or Payment.objects.filter(external_id=invoice_number).first()
    )

    if payment:
        logger.info(f"[PayPal Webhook] Matched payment ID: {payment.id}")
        PaymentEvent.objects.create(
            payment=payment,
            gateway="paypal",
            event_type=event_type,
            raw_data=payload,
        )

        if event_type == "PAYMENT.SALE.COMPLETED":
            update_payment_status(payment.external_id, "completed")
            logger.info(
                f"[PayPal Webhook] Updated payment status to completed for {payment.id}"
            )
    else:
        logger.warning(
            f"[PayPal Webhook] No payment found for external ID: {fallback_id} or invoice: {invoice_number}"
        )

    return HttpResponse(status=200)
