# paystack_api/webhook.py
import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_paystack_webhook(request):
    payload = json.loads(request.body)
    event = payload.get("event")
    data = payload.get("data")

    if not event or not data:
        return HttpResponse(status=400)

    reference = data.get("reference")
    if not reference:
        return HttpResponse(status=400)

    try:
        payment = Payment.objects.filter(
            external_id=reference, gateway="paystack"
        ).first()

        if not payment:
            logger.warning(
                f"[Paystack Webhook] Payment not found for reference: {reference}"
            )
            return HttpResponse(status=200)  # Still return 200 to prevent retries

        PaymentEvent.objects.create(
            payment=payment,
            gateway="paystack",
            event_type=event,
            payload=payload,
        )

        if event == "charge.success":
            update_payment_status(reference, "completed", gateway="paystack")

            metadata = data.get("metadata", {})
            paper_id = metadata.get("paper_id")
            user_id = metadata.get("user_id")

            if paper_id and user_id and payment.order:
                try:
                    from exampapers.models import Paper

                    paper = Paper.objects.get(pk=paper_id)
                    if not payment.order.papers.filter(pk=paper.pk).exists():
                        payment.order.papers.add(paper)
                except Exception as e:
                    logger.exception(f"[Paystack Webhook] Error adding paper: {e}")

    except Exception as e:
        logger.exception(f"[Paystack Webhook] Unexpected error: {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)
