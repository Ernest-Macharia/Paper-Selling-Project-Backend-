from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response     import Response
from rest_framework              import status

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from requests.auth import HTTPBasicAuth
import json
from . mpesa_credentials import MpesaAccessToken, LipanaMpesaPpassword
from django.views.decorators.csrf import csrf_exempt
from .models import MpesaPayment
from .utils    import get_mpesa_access_token, initiate_stk_push
from django.utils.dateparse     import parse_datetime
from exampapers.models import Order
from django.conf import settings


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def lipa_na_mpesa_direct(request):
    """
    POST payload:
      {
        "phone_number": "2547XXXXXXXX",
        "amount": 100.00
      }
    """
    phone = request.data.get('phone_number')
    amount_raw = request.data.get('amount')

    # Validate phone number
    if not phone:
        return Response(
            {"detail": "phone_number is required"},
            status=status.HTTP_400_BAD_REQUEST
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
            status=status.HTTP_400_BAD_REQUEST
        )

    # Call Daraja API
    resp = initiate_stk_push(phone, amount)

    merchant_req_id = resp.get('MerchantRequestID')
    checkout_req_id = resp.get('CheckoutRequestID')
    response_code = resp.get('ResponseCode')

    # Record the transaction without order
    MpesaPayment.objects.create(
        amount=amount,
        phone_number=phone,
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        status='Pending' if response_code == '0' else 'Failed'
    )

    return Response(resp, status=status.HTTP_200_OK)

@api_view(['POST'])
@csrf_exempt
def mpesa_callback(request):
    cb = request.data.get('Body', {}).get('stkCallback', {})
    checkout_id = cb.get('CheckoutRequestID')
    result_code = cb.get('ResultCode')

    try:
        payment = MpesaPayment.objects.get(checkout_request_id=checkout_id)
    except MpesaPayment.DoesNotExist:
        return Response({'error': 'Unknown CheckoutRequestID'}, status=status.HTTP_400_BAD_REQUEST)

    if result_code == 0:
        items  = cb.get('CallbackMetadata', {}).get('Item', [])
        receipt= next(item['Value'] for item in items if item['Name']=='MpesaReceiptNumber')
        amt    = next(item['Value'] for item in items if item['Name']=='Amount')
        ts     = next(item['Value'] for item in items if item['Name']=='TransactionDate')

        payment.status               = 'Completed'
        payment.mpesa_receipt_number = receipt
        payment.transaction_date     = parse_datetime(str(ts))
        payment.save()

        # mark order paid
        order = payment.order
        order.status = 'completed'
        order.save()
    else:
        payment.status = 'Failed'
        payment.save()

    return Response({'ResultCode':0,'ResultDesc':'Accepted'}, status=status.HTTP_200_OK)

# def getAccessToken(request):
#     consumer_key = '8pKiLZ8qR3K0wNAYYyJUBvRK6KOvT5Od6mZHmdka42Tm7vYh'
#     consumer_secret = '49X9GJd7agrHfomIiKp6LbroNt8zroLRPrKejLgSOJtJ3hm4OqTHAHQlu0VhABoq'
#     api_URL = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'

#     r = requests.get(api_URL, auth=HTTPBasicAuth(consumer_key, consumer_secret))
#     mpesa_access_token = json.loads(r.text)
#     validated_mpesa_access_token = mpesa_access_token['access_token']

#     return HttpResponse(validated_mpesa_access_token)


# def lipa_na_mpesa_online(request):
#     access_token = MpesaAccessToken.validated_mpesa_access_token
#     api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
#     headers = {"Authorization": "Bearer %s" % access_token}
#     request = {
#         "BusinessShortCode": LipanaMpesaPpassword.Business_short_code,
#         "Password": LipanaMpesaPpassword.decode_password,
#         "Timestamp": LipanaMpesaPpassword.lipa_time,
#         "TransactionType": "CustomerPayBillOnline",
#         "Amount": 1,
#         "PartyA": 254710992763,  # replace with your phone number to get stk push
#         "PartyB": LipanaMpesaPpassword.Business_short_code,
#         "PhoneNumber": 254710992763,  # replace with your phone number to get stk push
#         "CallBackURL": "https://sandbox.safaricom.co.ke/mpesa/",
#         "AccountReference": "Ernest",
#         "TransactionDesc": "Testing stk push"
#     }

#     response = requests.post(api_url, json=request, headers=headers)
#     return HttpResponse(response.text)

# @csrf_exempt
# def register_urls(request):
#     access_token = MpesaAccessToken.validated_mpesa_access_token
#     api_url = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
#     headers = {"Authorization": "Bearer %s" % access_token}
#     options = {"ShortCode": LipanaMpesaPpassword.Business_short_code,
#                "ResponseType": "Completed",
#                "ConfirmationURL": "59ba-41-90-172-59.ngrok-free.app/api/mpesa_api/c2b/confirmation",
#                "ValidationURL": "59ba-41-90-172-59.ngrok-free.app/api/mpesa_api/c2b/validation"}
#     response = requests.post(api_url, json=options, headers=headers)
#     return HttpResponse(response.text)

# @csrf_exempt
# def call_back(request):
#     pass

# @csrf_exempt
# def validation(request):
#     context = {
#         "ResultCode": 0,
#         "ResultDesc": "Accepted"
#     }
#     return JsonResponse(dict(context))

# @csrf_exempt
# def confirmation(request):
#     mpesa_body =request.body.decode('utf-8')
#     mpesa_payment = json.loads(mpesa_body)
#     payment = MpesaPayment(
#         first_name=mpesa_payment['FirstName'],
#         last_name=mpesa_payment['LastName'],
#         middle_name=mpesa_payment['MiddleName'],
#         description=mpesa_payment['TransID'],
#         phone_number=mpesa_payment['MSISDN'],
#         amount=mpesa_payment['TransAmount'],
#         reference=mpesa_payment['BillRefNumber'],
#         organization_balance=mpesa_payment['OrgAccountBalance'],
#         type=mpesa_payment['TransactionType'],
#     )
#     payment.save()
#     context = {
#         "ResultCode": 0,
#         "ResultDesc": "Accepted"
#     }
#     return JsonResponse(dict(context))
