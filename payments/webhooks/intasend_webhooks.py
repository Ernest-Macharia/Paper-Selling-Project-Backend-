import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment
from payments.services.payment_update_service import update_payment_status

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_intasend_event(request):
    """Webhook endpoint for IntaSend payment updates."""
    try:
        payload = json.loads(request.body)
        logger.info(f"[IntaSend Webhook] Payload: {payload}")

        invoice_id = payload.get("invoice_id")
        status = payload.get("state")

        payment = Payment.objects.filter(
            external_id=invoice_id, gateway="intasend"
        ).first()
        if not payment:
            logger.warning(f"[IntaSend Webhook] No payment found for {invoice_id}")
            return HttpResponse(status=404)

        if status == "COMPLETE":
            update_payment_status(invoice_id, "completed", gateway="intasend")
        elif status == "FAILED":
            update_payment_status(invoice_id, "failed", gateway="intasend")
        else:
            update_payment_status(invoice_id, "pending", gateway="intasend")

        return HttpResponse(status=200)

    except Exception as e:
        logger.exception(f"[IntaSend Webhook] Error processing webhook: {e}")
        return HttpResponse(status=500)
