import logging

import requests
from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exampapers.models import Order
from payments import serializers
from payments.emails import send_withdrawal_email_async
from payments.serializers import WithdrawalRequestSerializer
from payments.services.payment_verification import (
    verify_paypal_payment,
    verify_stripe_payment,
)
from payments.services.payout_service import disburse_withdrawal
from paypal_api.models import PayPalPayment
from stripe_api.models import StripePayment

from .models import Payment, UserPayoutProfile, Wallet, WithdrawalRequest
from .serializers import PaymentSerializer, WalletSummarySerializer

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60


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
        user = self.request.user
        status = self.request.query_params.get("status")
        queryset = WithdrawalRequest.objects.filter(user=user).order_by("-created_at")
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        amount = serializer.validated_data["amount"]
        wallet = user.wallet
        logger.debug(f"User {user.id} requested withdrawal of amount {amount}")

        profile = getattr(user, "userpayoutprofile", None)
        if not profile or not profile.preferred_method:
            logger.warning(f"User {user.id} has no payout method set")
            raise serializers.ValidationError("You must set up a payout method first.")

        if wallet.available_balance < amount:
            logger.warning(f"User {user.id} has insufficient balance")
            raise serializers.ValidationError("Insufficient available balance.")

        wallet.available_balance -= amount
        wallet.total_withdrawn += amount
        wallet.last_withdrawal_at = timezone.now()
        wallet.save(
            update_fields=["available_balance", "total_withdrawn", "last_withdrawal_at"]
        )
        logger.debug(f"Updated wallet for user {user.id}")

        withdrawal = serializer.save(user=user, status="approved")
        logger.info(f"Created withdrawal {withdrawal.id} for user {user.id}")

        send_withdrawal_email_async.delay(
            user.id,
            withdrawal.id,
            "withdrawal_requested_email.html",
            "Your GradesWorld Withdrawal Request",
        )

        try:
            result = disburse_withdrawal(withdrawal)
            logger.info(f"Disbursement result for withdrawal {withdrawal.id}: {result}")
        except Exception:
            logger.exception(f"Disbursement crashed for withdrawal {withdrawal.id}")
            raise serializers.ValidationError("Withdrawal disbursement failed.")

        if result.get("status") != "success":
            withdrawal.status = "failed"
            withdrawal.save(update_fields=["status"])
            logger.error(f"Withdrawal {withdrawal.id} failed: {result.get('error')}")

            send_withdrawal_email_async.delay(
                user.id,
                withdrawal.id,
                "withdrawal_failed_email.html",
                "Withdrawal Failed – GradesWorld",
            )

            raise serializers.ValidationError(
                f"Withdrawal failed: {result.get('error')}"
            )


class WalletSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSummarySerializer(wallet)
        return Response(serializer.data)


class PayoutInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        try:
            wallet, _ = Wallet.objects.get_or_create(user=user)
            profile, _ = UserPayoutProfile.objects.get_or_create(user=user)

            return Response(
                {
                    "balance": wallet.available_balance,
                    "preferred_method": profile.preferred_method,
                    "paypal_email": profile.paypal_email,
                    "stripe_account_id": profile.stripe_account_id,
                    "mpesa_phone": profile.mpesa_phone,
                    "last_withdrawal_at": wallet.last_withdrawal_at,
                }
            )
        except Exception as e:
            # log this in production
            return Response(
                {"detail": f"Failed to load payout info: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@permission_classes([IsAuthenticated])
def stripe_oauth_callback(request):
    code = request.GET.get("code")
    if not code:
        return JsonResponse({"error": "Missing code from Stripe"}, status=400)

    data = {
        "client_secret": settings.STRIPE_SECRET_KEY,
        "code": code,
        "grant_type": "authorization_code",
    }

    response = requests.post(
        "https://connect.stripe.com/oauth/token", data=data, timeout=DEFAULT_TIMEOUT
    )
    if response.status_code != 200:
        return JsonResponse({"error": "Failed to get Stripe account"}, status=400)

    stripe_user_id = response.json().get("stripe_user_id")
    UserPayoutProfile.objects.update_or_create(
        user=request.user, defaults={"stripe_account_id": stripe_user_id}
    )

    baseUrl = settings.BASE_URL
    # Redirect back to the frontend (you can customize this)
    return HttpResponseRedirect(baseUrl + "/dashboard/earnings")


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_payout_info(request):
    user = request.user
    profile, _ = UserPayoutProfile.objects.get_or_create(user=user)

    paypal_email = request.data.get("paypal_email")
    mpesa_phone = request.data.get("mpesa_phone")

    if paypal_email:
        profile.paypal_email = paypal_email
    if mpesa_phone:
        profile.mpesa_phone = mpesa_phone

    profile.save()
    return Response(
        {
            "success": True,
            "paypal_email": profile.paypal_email,
            "mpesa_phone": profile.mpesa_phone,
        }
    )
