from rest_framework import serializers

from .models import Payment, WithdrawalRequest


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "status", "currency", "created_at"]


class CheckoutInitiateSerializer(serializers.Serializer):
    paper_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    payment_method = serializers.ChoiceField(choices=["paypal", "stripe", "mpesa"])
    # amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    # currency = serializers.CharField(max_length=3)
    # phone_number = serializers.CharField(required=False)


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = ["id", "amount", "method", "data", "status", "created_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        profile = getattr(user, "userpayoutprofile", None)
        method = attrs["method"]

        if not profile:
            raise serializers.ValidationError("Payout profile not configured.")

        if method == "paypal" and not profile.paypal_email:
            raise serializers.ValidationError("PayPal email is missing.")
        if method == "stripe" and not profile.stripe_account_id:
            raise serializers.ValidationError("Stripe account is missing.")
        if method == "mpesa" and not profile.mpesa_phone:
            raise serializers.ValidationError("M-Pesa number is missing.")

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        return WithdrawalRequest.objects.create(user=user, **validated_data)
