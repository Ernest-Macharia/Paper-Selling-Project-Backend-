import base64
from datetime import datetime

import requests
from django.conf import settings

DEFAULT_TIMEOUT = 60


def get_mpesa_access_token():
    consumer_key = settings.MPESA_CONSUMER_KEY
    consumer_secret = settings.MPESA_CONSUMER_SECRET
    auth_url = settings.MPESA_AUTH_URL

    response = requests.get(
        auth_url, auth=(consumer_key, consumer_secret), timeout=DEFAULT_TIMEOUT
    )
    response_data = response.json()
    return response_data["access_token"]


def send_money_b2c(phone_number, amount, access_token, remarks="", occasion="Payout"):
    url = (
        "https://api.safaricom.co.ke/mpesa/b2c/v1/paymentrequest"
        if settings.MPESA_ENV == "live"
        else "https://sandbox.safaricom.co.ke/mpesa/b2c/v1/paymentrequest"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "InitiatorName": settings.MPESA_INITIATOR_NAME,
        "SecurityCredential": settings.MPESA_SECURITY_CREDENTIAL,
        "CommandID": "BusinessPayment",
        "Amount": str(amount),
        "PartyA": settings.MPESA_SHORTCODE,
        "PartyB": phone_number,
        "Remarks": remarks,
        "QueueTimeOutURL": settings.MPESA_TIMEOUT_URL,
        "ResultURL": settings.MPESA_RESULT_URL,
        "Occasion": occasion,
    }

    response = requests.post(
        url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT
    )

    try:
        return response.json()
    except Exception:
        return {"error": "Failed to parse response", "raw": response.text}


def initiate_stk_push(phone_number, amount, order_id=None):
    access_token = get_mpesa_access_token()

    shortcode = settings.MPESA_SHORTCODE
    passkey = settings.MPESA_PASSKEY
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode((shortcode + passkey + timestamp).encode()).decode()
    acct_ref = order_id or phone_number[-6:]
    desc = order_id and f"Order {order_id}" or f"Pay:{amount}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone_number,
        "PartyB": shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": acct_ref,
        "TransactionDesc": desc,
    }

    stk_push_url = settings.MPESA_STK_PUSH_URL
    response = requests.post(
        stk_push_url, json=payload, headers=headers, timeout=DEFAULT_TIMEOUT
    )
    return response.json()
