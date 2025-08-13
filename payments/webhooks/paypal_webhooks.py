import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.models import Payment
from payments.services.payment_update_service import update_payment_status
from payments.utils.paypal_verification import verify_paypal_signature
from paypal_api.models import PayPalPayment

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_paypal_event(request):
    try:
        payload = json.loads(request.body)
        event_type = payload.get("event_type")
        resource = payload.get("resource", {})
        order_id = resource.get("id")

        logger.info(f"Received PayPal webhook: {event_type} for order {order_id}")

        if not verify_paypal_signature(request):
            return HttpResponse("Invalid signature", status=400)

        try:
            payment = Payment.objects.get(external_id=order_id, gateway="paypal")
            order = payment.order

            if event_type == "PAYMENT.CAPTURE.COMPLETED":
                # Update payment status
                payment.status = "completed"
                payment.save()

                # Update PayPal payment record
                paypal_payment = PayPalPayment.objects.get(payment=payment)
                paypal_payment.status = "captured"
                paypal_payment.transaction_id = resource.get("id")
                paypal_payment.save()

                # Update order status
                order.status = "completed"
                order.save()

                # Update wallet balances
                update_payment_status(payment.external_id, "completed", "paypal")

            elif event_type == "PAYMENT.CAPTURE.DENIED":
                order.status = "failed"
                order.save()
                payment.status = "failed"
                payment.save()

        except Payment.DoesNotExist:
            logger.warning(f"Payment not found for PayPal order {order_id}")

        return HttpResponse(status=200)

    except Exception as e:
        logger.error(f"Error processing PayPal webhook: {str(e)}")
        return HttpResponse(status=500)
