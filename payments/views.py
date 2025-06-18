from rest_framework import permissions, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exampapers.models import Order, Paper
from payments.services.checkout_service import handle_checkout

from .models import Payment
from .serializers import CheckoutInitiateSerializer, PaymentSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]


class CheckoutInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutInitiateSerializer(data=request.data)
        if serializer.is_valid():
            paper_ids = serializer.validated_data["paper_ids"]
            payment_method = serializer.validated_data["payment_method"]
            user = request.user

            try:
                papers = Paper.objects.get(id=paper_ids)
            except Paper.DoesNotExist:
                return Response({"error": "Paper not found"}, status=404)

            order = Order.objects.create(
                user=user, papers=papers, price=papers.price, status="pending"
            )

            try:
                result = handle_checkout(payment_method, order)
            except ValueError as e:
                return Response({"error": str(e)}, status=400)

            return Response(
                {
                    "message": "Checkout initiated",
                    "order_id": order.id,
                    "checkout_info": result,
                },
                status=201,
            )

        return Response(serializer.errors, status=400)
