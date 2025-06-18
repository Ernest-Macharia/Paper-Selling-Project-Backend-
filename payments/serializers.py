from rest_framework import serializers

from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class CheckoutInitiateSerializer(serializers.Serializer):
    paper_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
    payment_method = serializers.ChoiceField(choices=["paypal", "stripe", "mpesa"])
    # amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    # currency = serializers.CharField(max_length=3)
    # phone_number = serializers.CharField(required=False)
