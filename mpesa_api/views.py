from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import MpesaPayment

# from .mpesa_credentials import LipanaMpesaPpassword, MpesaAccessToken
from .utils import initiate_stk_push


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def lipa_na_mpesa_direct(request):
    """
    POST payload:
      {
        "phone_number": "2547XXXXXXXX",
        "amount": 100.00
      }
    """
    phone = request.data.get("phone_number")
    amount_raw = request.data.get("amount")

    # Validate phone number
    if not phone:
        return Response(
            {"detail": "phone_number is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate amount
    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        amount = int(round(amount))  # Safaricom requires integer amount
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid amount. Please provide a positive numeric amount."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Call Daraja API
    resp = initiate_stk_push(phone, amount)

    merchant_req_id = resp.get("MerchantRequestID")
    checkout_req_id = resp.get("CheckoutRequestID")
    response_code = resp.get("ResponseCode")

    # Record the transaction without order
    MpesaPayment.objects.create(
        amount=amount,
        phone_number=phone,
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        status="Pending" if response_code == "0" else "Failed",
    )

    return Response(resp, status=status.HTTP_200_OK)


@api_view(["POST"])
@csrf_exempt
def mpesa_callback(request):
    cb = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = cb.get("CheckoutRequestID")
    result_code = cb.get("ResultCode")

    try:
        payment = MpesaPayment.objects.get(checkout_request_id=checkout_id)
    except MpesaPayment.DoesNotExist:
        return Response(
            {"error": "Unknown CheckoutRequestID"}, status=status.HTTP_400_BAD_REQUEST
        )

    if result_code == 0:
        items = cb.get("CallbackMetadata", {}).get("Item", [])
        receipt = next(
            item["Value"] for item in items if item["Name"] == "MpesaReceiptNumber"
        )
        # amt = next(item["Value"] for item in items if item["Name"] == "Amount")
        ts = next(item["Value"] for item in items if item["Name"] == "TransactionDate")

        payment.status = "Completed"
        payment.mpesa_receipt_number = receipt
        payment.transaction_date = parse_datetime(str(ts))
        payment.save()

        # mark order paid
        order = payment.order
        order.status = "completed"
        order.save()
    else:
        payment.status = "Failed"
        payment.save()

    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK
    )
