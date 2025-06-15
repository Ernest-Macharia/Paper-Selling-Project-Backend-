import paypalrestsdk
from django.conf import settings

from payments.models import Payment
from paypal_api.models import PayPalPayment

paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


def handle_paypal_checkout(data):
    payment_obj = paypalrestsdk.Payment(
        {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {
                        "total": f"{data['amount']:.2f}",
                        "currency": data["currency"],
                    },
                    "description": data.get("description", "Order"),
                }
            ],
            "redirect_urls": {
                "return_url": settings.PAYPAL_SUCCESS_URL,
                "cancel_url": settings.PAYPAL_CANCEL_URL,
            },
        }
    )

    if not payment_obj.create():
        raise Exception(payment_obj.error)

    approval_url = next(
        (link.href for link in payment_obj.links if link.rel == "approval_url"), None
    )

    # Create unified payment record
    payment = Payment.objects.create(
        gateway="paypal",
        external_id=payment_obj.id,
        amount=data["amount"],
        currency=data["currency"],
        customer_email=data.get("email"),
        description=data.get("description"),
        status="created",
    )

    PayPalPayment.objects.create(payment=payment, paypal_order_id=payment_obj.id)

    return {"checkout_url": approval_url, "order_id": payment_obj.id}
