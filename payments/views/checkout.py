from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exampapers.models import Order, Paper
from payments.serializers import CheckoutInitiateSerializer
from payments.services.checkout_service import handle_checkout

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def unified_checkout(request):
    serializer = CheckoutInitiateSerializer(data=request.data)
    if serializer.is_valid():
        order = serializer.validated_data["order"]
        provider = serializer.validated_data["provider"]
        result = handle_checkout(provider, order)
        return Response(result)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckoutInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutInitiateSerializer(data=request.data)
        if serializer.is_valid():
            paper_ids = serializer.validated_data["paper_ids"]
            payment_method = serializer.validated_data["payment_method"]

            # user = User.objects.first()
            user = request.user  # Use the authenticated user

            total_price = 0
            papers = []
            for pid in paper_ids:
                try:
                    paper = Paper.objects.get(id=pid)
                except Paper.DoesNotExist:
                    return Response(
                        {"error": f"Paper with id {pid} not found."}, status=404
                    )
                total_price += paper.price
                papers.append(paper)

            order = Order.objects.create(user=user, price=total_price, status="pending")
            order.papers.add(*papers)

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
