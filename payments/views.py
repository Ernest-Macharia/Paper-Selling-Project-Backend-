from rest_framework import permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from exampapers.models import Order
from payments.serializers import WithdrawalRequestSerializer
from payments.services.payment_verification import (
    verify_paypal_payment,
    verify_stripe_payment,
)
from paypal_api.models import PayPalPayment
from stripe_api.models import StripePayment

from .models import Payment, WithdrawalRequest
from .serializers import PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order").prefetch_related("order__papers")
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    session_id = (
        request.query_params.get("session_id")
        or request.query_params.get("paymentId")
        or request.query_params.get("token")
    )
    order_id = request.query_params.get("order_id")

    if not order_id:
        return Response({"detail": "Missing order_id."}, status=400)

    if not session_id:
        return Response({"detail": "Missing session_id."}, status=400)

    try:
        order = Order.objects.get(id=order_id)

        if order.status == "completed":
            return Response(
                {
                    "success": True,
                    "order": {
                        "id": order.id,
                        "paper_ids": [p.id for p in order.papers.all()],
                    },
                }
            )

        if session_id:
            if session_id.startswith("cs_"):
                success = verify_stripe_payment(session_id, order)
            else:
                success = verify_paypal_payment(session_id, order)
        else:
            # Try to get StripePayment
            stripe_record = StripePayment.objects.filter(payment__order=order).first()
            if stripe_record:
                session_id = stripe_record.session_id
                success = verify_stripe_payment(session_id, order)
            else:
                # Fallback to PayPal
                paypal_record = PayPalPayment.objects.filter(
                    payment__order=order
                ).first()
                if not paypal_record:
                    return Response(
                        {"success": False, "error": "No payment session found."},
                        status=400,
                    )
                session_id = paypal_record.paypal_order_id
                success = verify_paypal_payment(session_id, order)

        return Response(
            {
                "success": success,
                "order": (
                    {
                        "id": order.id,
                        "paper_ids": [p.id for p in order.papers.all()],
                    }
                    if success
                    else None
                ),
            }
        )

    except Order.DoesNotExist:
        return Response({"success": False, "error": "Order not found."}, status=404)


class WithdrawalRequestViewSet(viewsets.ModelViewSet):
    serializer_class = WithdrawalRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WithdrawalRequest.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save()
