from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from mpesa_api.checkout import handle_mpesa_checkout
from paypal_api.checkout import handle_paypal_checkout
from stripe_api.checkout import handle_stripe_checkout

from .models import Payment
from .serializers import PaymentCheckoutSerializer, PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]


@api_view(["POST"])
@permission_classes([AllowAny])
def unified_checkout(request):
    serializer = PaymentCheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    provider = data["provider"]

    try:
        if provider == "stripe":
            result = handle_stripe_checkout(data)
        elif provider == "paypal":
            result = handle_paypal_checkout(data)
        elif provider == "mpesa":
            result = handle_mpesa_checkout(data)
        else:
            return Response({"detail": "Unsupported provider"}, status=400)

        return Response(result, status=200)
    except Exception as e:
        return Response({"detail": str(e)}, status=500)
