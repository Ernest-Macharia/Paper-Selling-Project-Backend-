# mpesa_app/views.py

from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from mpesa_api.models import MpesaPayment
from mpesa_api.utils import initiate_stk_push
from payments.models import Payment


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def lipa_na_mpesa_direct(request):
    """
    Initiate Mpesa STK Push
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

    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError("Amount must be positive")
        amount = int(round(amount))
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid amount. Please provide a positive numeric amount."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Call Daraja API to initiate STK push
    resp = initiate_stk_push(phone, amount)

    merchant_req_id = resp.get("MerchantRequestID")
    checkout_req_id = resp.get("CheckoutRequestID")
    response_code = resp.get("ResponseCode")

    # Save initial MpesaPayment with status Pending or Failed
    MpesaPayment.objects.create(
        amount=amount,
        phone_number=phone,
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        status="Pending" if response_code == "0" else "Failed",
    )

    return Response(resp, status=status.HTTP_200_OK)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def mpesa_callback(request):
    """
    Mpesa Daraja Callback URL
    """
    cb = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = cb.get("CheckoutRequestID")
    result_code = cb.get("ResultCode")

    try:
        payment_record = MpesaPayment.objects.get(checkout_request_id=checkout_id)
    except MpesaPayment.DoesNotExist:
        return Response(
            {"error": "Unknown CheckoutRequestID"}, status=status.HTTP_400_BAD_REQUEST
        )

    if result_code == 0:
        # Payment success
        items = cb.get("CallbackMetadata", {}).get("Item", [])
        receipt = next(
            item["Value"] for item in items if item["Name"] == "MpesaReceiptNumber"
        )
        amt = next(item["Value"] for item in items if item["Name"] == "Amount")
        ts = next(item["Value"] for item in items if item["Name"] == "TransactionDate")
        phone = payment_record.phone_number
        merchant_req_id = payment_record.merchant_request_id

        # Create or update unified Payment record
        payment_obj, created = Payment.objects.update_or_create(
            external_id=checkout_id,
            defaults={
                "gateway": "mpesa",
                "amount": amt,
                "status": "completed",
                "currency": "KES",
                "description": "Mpesa STK Push",
            },
        )

        # Update MpesaPayment record
        MpesaPayment.objects.update_or_create(
            payment=payment_obj,
            defaults={
                "checkout_request_id": checkout_id,
                "merchant_request_id": merchant_req_id,
                "mpesa_receipt_number": receipt,
                "phone_number": phone,
                "transaction_date": parse_datetime(str(ts)),
                "status": "Completed",
            },
        )

        # ✅ If you want: update related Order model here

    else:
        # Payment failed
        payment_record.status = "Failed"
        payment_record.save()

    return Response(
        {"ResultCode": 0, "ResultDesc": "Accepted"}, status=status.HTTP_200_OK
    )
