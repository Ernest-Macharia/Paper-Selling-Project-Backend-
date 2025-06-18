# payments_core/services/refund_service.py

from payments.models import Payment, PaymentEvent
from paypal_api.refund import process_paypal_refund
from stripe_api.refund import process_stripe_refund

# from mpesa_api.refund import process_mpesa_refund


def process_refund(payment_id):
    payment = Payment.objects.get(id=payment_id)

    # Log refund requested event
    PaymentEvent.objects.create(
        payment=payment,
        gateway=payment.payment_method,
        event_type="refund_requested",
        payload={},
    )

    if payment.payment_method == "stripe":
        result = process_stripe_refund(payment)
    elif payment.payment_method == "paypal":
        result = process_paypal_refund(payment)
    # elif payment.payment_method == 'mpesa':
    #     result = process_mpesa_refund(payment)
    else:
        result = {"status": "failed", "error": "Unsupported gateway"}

    # Log success/failure event
    PaymentEvent.objects.create(
        payment=payment,
        gateway=payment.payment_method,
        event_type=(
            "refund_succeeded" if result["status"] == "success" else "refund_failed"
        ),
        payload=result,
    )

    return result
