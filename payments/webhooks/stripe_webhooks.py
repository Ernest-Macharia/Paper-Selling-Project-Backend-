import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from exampapers.models import Order, Paper
from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def handle_stripe_event(event):
    event_type = event["type"]
    session = event["data"]["object"]
    external_id = session.get("id")

    if not external_id:
        return HttpResponse(status=400)

    payment = Payment.objects.filter(external_id=external_id).first()

    PaymentEvent.objects.create(
        payment=payment,
        gateway="stripe",
        event_type=event_type,
        raw_data=session,
    )

    if event["type"] == "checkout.session.completed" and payment:
        update_payment_status(external_id, "completed", gateway="stripe")

        metadata = session.get("metadata", {})
        paper_id = metadata.get("paper_id")
        user_id = metadata.get("user_id")

        if paper_id and user_id:
            try:
                paper = Paper.objects.get(pk=paper_id)
                user = get_user_model().objects.get(pk=user_id)

                # Create or reuse an order, and attach the paper
                order, _ = Order.objects.get_or_create(user=user, status="completed")
                order.papers.add(paper)
            except Exception as e:
                print(f"[Webhook Error] Failed to associate paper: {e}")

    return HttpResponse(status=200)
