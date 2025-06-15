from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class PaymentCheckoutSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=["stripe", "paypal", "mpesa"])
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=10)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
