from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from payments.services.refund_service import process_refund


@api_view(["POST"])
def refund_payment(request, payment_id):
    result = process_refund(payment_id)

    if result["status"] == "success":
        return Response(result)
    else:
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
