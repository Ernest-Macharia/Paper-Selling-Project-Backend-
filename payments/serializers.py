from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import Payment, Wallet, WithdrawalRequest


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "currency", "created_at"]


class CheckoutInitiateSerializer(serializers.Serializer):
    paper_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    payment_method = serializers.ChoiceField(
        choices=["paypal", "stripe", "mpesa", "pesapal", "paystack", "intasend"]
    )
    # amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    # currency = serializers.CharField(max_length=3)
    # phone_number = serializers.CharField(required=False)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ["id", "amount", "method", "destination", "status", "created_at"]
        read_only_fields = ["destination", "status", "created_at"]

    def validate(self, data):
        user = self.context["request"].user
        amount = data.get("amount")
        method = data.get("method")

        if amount < 10:
            raise serializers.ValidationError("Minimum withdrawal amount is $10.")

        if amount > user.wallet.available_balance:
            raise serializers.ValidationError("Insufficient wallet balance.")

        recent = WithdrawalRequest.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(hours=6),
            status__in=["pending", "approved"],
        )
        if recent.exists():
            raise serializers.ValidationError(
                "You already have a recent withdrawal request."
            )

        profile = getattr(user, "userpayoutprofile", None)
        if not profile:
            raise serializers.ValidationError("No payout profile configured.")

        if method == "stripe":
            destination = profile.stripe_account_id
        elif method == "paypal":
            destination = profile.paypal_email
        elif method == "mpesa":
            destination = profile.mpesa_phone
        else:
            raise serializers.ValidationError("Invalid payout method selected.")

        if not destination:
            raise serializers.ValidationError(f"No destination set for {method}.")

        data["destination"] = destination
        return data


class WalletSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            "available_balance",
            "total_earned",
            "total_withdrawn",
            "last_withdrawal_at",
            "last_updated",
            "currency",
        ]
