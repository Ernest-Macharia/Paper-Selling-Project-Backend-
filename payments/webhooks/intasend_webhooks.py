import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment
from payments.services.payment_update_service import update_payment_status

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_intasend_event(request):
    """Webhook endpoint for IntaSend payment updates."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        logger.info(f"[IntaSend Webhook] Payload: {payload}")

        # Optional: Verify challenge token (recommended by IntaSend)
        challenge = request.headers.get("IntaSend-Challenge")
        expected_challenge = getattr(settings, "INTASEND_WEBHOOK_CHALLENGE", None)
        if expected_challenge and challenge != expected_challenge:
            logger.warning("[IntaSend Webhook] Invalid challenge token")
            return JsonResponse({"error": "Invalid challenge token"}, status=403)

        # IntaSend payload sometimes comes with 'data' key
        data = payload.get("data", payload)
        invoice_id = data.get("invoice_id")
        status = data.get("state")

        if not invoice_id:
            logger.error("[IntaSend Webhook] Missing invoice_id in payload")
            return JsonResponse({"error": "Missing invoice_id"}, status=400)

        payment = Payment.objects.filter(
            external_id=invoice_id, gateway="intasend"
        ).first()

        if not payment:
            logger.warning(
                f"[IntaSend Webhook] No payment found for invoice {invoice_id}"
            )
            return JsonResponse({"error": "Payment not found"}, status=404)

        # Idempotency check — avoid re-updating completed payments
        if payment.status == "completed" and status == "COMPLETE":
            logger.info(
                f"[IntaSend Webhook] Payment {invoice_id} already completed, skipping."
            )
            return JsonResponse({"status": "already completed"}, status=200)

        # Map IntaSend states to internal statuses
        if status in ["COMPLETE", "SUCCESSFUL"]:
            update_payment_status(invoice_id, "completed", gateway="intasend")
        elif status in ["FAILED", "CANCELLED"]:
            update_payment_status(invoice_id, "failed", gateway="intasend")
        else:
            update_payment_status(invoice_id, "pending", gateway="intasend")

        logger.info(f"[IntaSend Webhook] Payment {invoice_id} updated to {status}")
        return JsonResponse({"status": "ok"}, status=200)

    except json.JSONDecodeError:
        logger.error("[IntaSend Webhook] Invalid JSON payload")
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    except Exception as e:
        logger.exception(f"[IntaSend Webhook] Unexpected error: {e}")
        return HttpResponse(status=500)
