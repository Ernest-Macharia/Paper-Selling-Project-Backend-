# paypal_app/views.py

import logging

import paypalrestsdk
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from payments.models import Payment

logger = logging.getLogger(__name__)
logger.info("PayPal SDK configured in %s mode", settings.PAYPAL_MODE)

# Configure PayPal SDK once when module is imported
paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


# Create PayPal payment
@api_view(["POST"])
@permission_classes([AllowAny])
def paypal_create(request):
    """
    POST { "amount": 12.34, "currency": "USD", "email":
        "client@email.com", "description": "Paper purchase" }
    """
    amount = request.data.get("amount")
    currency = request.data.get("currency", "USD")
    email = request.data.get("email")
    description = request.data.get("description", "Paper purchase")

    if amount is None:
        return Response(
            {"detail": "amount required"}, status=status.HTTP_400_BAD_REQUEST
        )

    payment = paypalrestsdk.Payment(
        {
            "intent": "sale",
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {"total": f"{float(amount):.2f}", "currency": currency},
                    "description": description,
                }
            ],
            "redirect_urls": {
                "return_url": settings.PAYPAL_RETURN_URL,
                "cancel_url": settings.PAYPAL_CANCEL_URL,
            },
        }
    )

    if not payment.create():
        logger.error("PayPal create error: %s", payment.error)
        return Response(payment.error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    approval_url = next(
        (link.href for link in payment.links if link.rel == "approval_url"), None
    )

    # Save record to unified Payment model
    Payment.objects.update_or_create(
        external_id=payment.id,
        defaults={
            "gateway": "paypal",
            "amount": float(amount),
            "status": "created",
            "currency": currency,
            "customer_email": email,
            "description": description,
        },
    )

    return Response({"orderID": payment.id, "approve_url": approval_url})


# Capture payment after user approves PayPal payment
@api_view(["POST"])
@permission_classes([AllowAny])
def paypal_capture(request):
    """
    POST { "orderID": "...", "payerID": "...", "payer_email": "..." }
    """
    order_id = request.data.get("orderID")
    payer_id = request.data.get("payerID")
    payer_email = request.data.get("payer_email")  # optional

    if not order_id or not payer_id:
        return Response(
            {"detail": "orderID and payerID required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payment = paypalrestsdk.Payment.find(order_id)
    except paypalrestsdk.ResourceNotFound as e:
        logger.error("Payment not found: %s", e)
        return Response(
            {"detail": "payment not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if not payment.execute({"payer_id": payer_id}):
        logger.error("PayPal execute error: %s", payment.error)
        return Response(payment.error, status=status.HTTP_400_BAD_REQUEST)

    # Update unified Payment model after successful capture
    Payment.objects.update_or_create(
        external_id=payment.id,
        defaults={
            "gateway": "paypal",
            "amount": float(payment.transactions[0].amount.total),
            "status": "completed",
            "currency": payment.transactions[0].amount.currency,
            "customer_email": payer_email,
            "description": payment.transactions[0].description,
        },
    )

    return Response(payment.to_dict())


# Success & Cancel Views (optional)
def paypal_payment_success(request):
    return HttpResponse(
        "<h1>✅ Payment was successful!</h1><p>Thank you for your purchase.</p>"
    )


def paypal_payment_cancelled(request):
    return HttpResponse(
        "<h1>❌ Payment was cancelled.</h1><p>You can try again at any time.</p>"
    )
