import logging

import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from exampapers.models import Paper
from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def handle_stripe_event(event):
    try:
        event_type = event.get("type")
        session = event.get("data", {}).get("object", {})
        external_id = session.get("id")

        if not event_type or not external_id:
            logger.warning("Invalid event payload: missing type or ID.")
            return HttpResponse(status=400)

        # Attempt to locate payment
        payment = Payment.objects.filter(
            external_id=external_id,
            gateway="stripe",
        ).first()

        if not payment:
            logger.warning(f"Payment not found for external_id={external_id}")
            return HttpResponse(status=404)

        # Log Stripe event
        PaymentEvent.objects.create(
            payment=payment,
            gateway="stripe",
            event_type=event_type,
            payload=session,
        )

        # Handle successful checkout
        if event_type == "checkout.session.completed":
            logger.info(f"Checkout session completed for payment {external_id}")
            update_payment_status(external_id, "completed", gateway="stripe")

            metadata = session.get("metadata", {})
            paper_id = metadata.get("paper_id")

            if paper_id:
                try:
                    paper = Paper.objects.get(pk=paper_id)
                    order = payment.order
                    if order and not order.papers.filter(id=paper.id).exists():
                        order.papers.add(paper)
                        logger.info(f"Paper {paper_id} added to order {order.id}")
                except Paper.DoesNotExist:
                    logger.warning(f"Paper {paper_id} does not exist.")
                except Exception as e:
                    logger.exception(f"[Stripe Metadata Error] {str(e)}")

        else:
            logger.info(f"Unhandled Stripe event type: {event_type}")

    except Exception as e:
        logger.exception(f"[Stripe Webhook Fatal Error] {e}")
        return HttpResponse(status=500)

    return HttpResponse(status=200)
