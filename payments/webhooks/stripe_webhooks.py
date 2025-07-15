import stripe
from django.conf import settings

# from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from exampapers.models import Paper
from payments.models import Payment, PaymentEvent
from payments.services.payment_update_service import update_payment_status

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def handle_stripe_event(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    try:
        event_type = event.get("type")
        session = event.get("data", {}).get("object", {})
        external_id = session.get("id")

        payment = Payment.objects.filter(
            external_id=external_id, gateway="stripe"
        ).first()

        if payment:
            PaymentEvent.objects.create(
                payment=payment,
                gateway="stripe",
                event_type=event_type,
                payload=session,
            )

        if event_type == "checkout.session.completed" and payment:
            update_payment_status(external_id, "completed", gateway="stripe")

            metadata = session.get("metadata", {})
            paper_id = metadata.get("paper_id")
            user_id = metadata.get("user_id")

            if paper_id and user_id:
                try:
                    paper = Paper.objects.get(pk=paper_id)
                    # user = get_user_model().objects.get(pk=user_id)

                    if (
                        payment.order
                        and not payment.order.papers.filter(pk=paper.pk).exists()
                    ):
                        payment.order.papers.add(paper)
                except Exception:
                    print("Error")

    except Exception:
        return HttpResponse(status=500)

    return HttpResponse(status=200)
