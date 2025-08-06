import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from exampapers.models import Order
from payments.services.payment_verification import verify_pesapal_payment
from payments.utils.paypal_verification import verify_paypal_signature
from payments.webhooks.mpesa_webhooks import handle_mpesa_event
from payments.webhooks.paypal_webhooks import handle_paypal_event
from payments.webhooks.stripe_webhooks import handle_stripe_event
from pesapal.models import PesapalPayment

logger = logging.getLogger(__name__)


@csrf_exempt
def stripe_webhook(request):
    return handle_stripe_event(request)


@csrf_exempt
def paypal_webhook(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)

    if not verify_paypal_signature(payload):
        return HttpResponse("Invalid signature", status=400)

    try:
        return handle_paypal_event(request)
    except Exception as e:
        logger.exception("[PayPal Webhook] Unexpected error: %s", e)
        return HttpResponse(status=500)


@csrf_exempt
def pesapal_callback_view(request, order_id):
    try:
        order_tracking_id = request.GET.get("OrderTrackingId")

        logger.info(f"Pesapal callback received for order {order_id}")

        # Get the payment records
        order = Order.objects.get(id=order_id)
        pesapal_payment = PesapalPayment.objects.get(
            order=order, tracking_id=order_tracking_id
        )

        # Update the Pesapal payment record
        pesapal_payment.raw_callback_data = dict(request.GET)
        pesapal_payment.save()

        if verify_pesapal_payment(order_tracking_id, order):
            pesapal_payment.status = "COMPLETED"
            pesapal_payment.save()
            return redirect(
                f"{settings.FRONTEND_URL}/payment/success?order_id={order_id}"
            )
        else:
            pesapal_payment.status = "FAILED"
            pesapal_payment.save()
            return redirect(
                f"{settings.FRONTEND_URL}/payment/failed?order_id={order_id}"
            )

    except (Order.DoesNotExist, PesapalPayment.DoesNotExist) as e:
        logger.error(f"Order/Payment not found: {str(e)}")
        return redirect(
            f"{settings.FRONTEND_URL}/payment/error?message=Order not found"
        )
    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return redirect(
            f"{settings.FRONTEND_URL}/payment/error?message=Payment processing error"
        )


@csrf_exempt
def mpesa_webhook(request):
    payload = json.loads(request.body)
    handle_mpesa_event(payload)
    return HttpResponse(status=200)
