import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from payments.services.payment_update_service import update_payment_status
from pesapal.models import PesapalPayment

logger = logging.getLogger(__name__)


@csrf_exempt
def handle_pesapal_event(request, order_id):
    try:
        payload = json.loads(request.body)
        order_tracking_id = payload.get("OrderTrackingId")

        logger.info(f"Pesapal IPN received for order {order_id}")

        # Get the payment records
        pesapal_payment = PesapalPayment.objects.get(
            order_id=order_id, tracking_id=order_tracking_id
        )

        # Update payment record with IPN data
        pesapal_payment.raw_callback_data = payload
        payment_status = payload.get("PaymentStatus")

        if payment_status == "COMPLETED":
            pesapal_payment.status = "COMPLETED"
            pesapal_payment.payment_method = payload.get("PaymentMethod")
            update_payment_status(
                pesapal_payment.payment.external_id, "completed", "pesapal"
            )
        elif payment_status == "FAILED":
            pesapal_payment.status = "FAILED"
            update_payment_status(
                pesapal_payment.payment.external_id, "failed", "pesapal"
            )

        pesapal_payment.save()

        return HttpResponse(status=200)

    except PesapalPayment.DoesNotExist:
        logger.warning(f"No Pesapal payment found for tracking ID: {order_tracking_id}")
        return HttpResponse("Payment not found", status=404)
    except Exception as e:
        logger.error(f"IPN processing error: {str(e)}")
        return HttpResponse(status=500)
