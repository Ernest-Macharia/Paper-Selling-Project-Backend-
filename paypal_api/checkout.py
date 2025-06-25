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


def handle_paypal_checkout(order):
    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

    baseURL = settings.BASE_URL

    # Create a temporary payment object to generate ID
    payment_obj = paypalrestsdk.Payment(
        {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {"total": f"{order.price:.2f}", "currency": "USD"},
                    "description": f"Purchase of {first_paper.title}",
                }
            ],
            "redirect_urls": {
                "return_url": f"{baseURL}/payment/success",
                "cancel_url": settings.PAYPAL_CANCEL_URL,
            },
        }
    )

    if not payment_obj.create():
        raise Exception(f"PayPal payment creation failed: {payment_obj.error}")

    approval_url = None
    for link in payment_obj.links:
        if link.rel == "approval_url":
            approval_url = str(link.href)
            break

    if not approval_url:
        raise Exception("Approval URL not found in PayPal response")

    # Save to database
    payment = Payment.objects.create(
        gateway="paypal",
        external_id=payment_obj.id,
        amount=order.price,
        currency="USD",
        description=f"Purchase of {first_paper.title}",
        status="created",
        order=order,
        customer_email=order.user.email,
    )

    PayPalPayment.objects.create(
        payment=payment,
        paypal_order_id=payment_obj.id,
    )

    return {
        "checkout_url": approval_url,
        "order_id": order.id,
        "session_id": payment_obj.id,  # use this to verify later
    }
