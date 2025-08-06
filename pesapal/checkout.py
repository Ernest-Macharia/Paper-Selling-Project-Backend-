import logging

import requests
from django.conf import settings

from payments.models import Payment
from pesapal.models import PesapalPayment

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 60


def get_pesapal_auth_token():
    """
    Get authentication token from Pesapal API with enhanced error handling
    """
    try:
        auth_url = f"{settings.PESAPAL_API_BASE}/api/Auth/RequestToken"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        payload = {
            "consumer_key": settings.PESAPAL_CONSUMER_KEY,
            "consumer_secret": settings.PESAPAL_CONSUMER_SECRET,
        }

        response = requests.post(
            auth_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("token")

    except requests.exceptions.RequestException as e:
        logger.error(f"Pesapal auth token request failed: {str(e)}")
        raise Exception("Failed to authenticate with Pesapal API")


def register_pesapal_ipn(ipn_url, auth_token):
    """
    Register IPN URL with Pesapal with improved validation
    """
    try:
        register_url = f"{settings.PESAPAL_API_BASE}/api/URLSetup/RegisterIPN"

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {"url": ipn_url, "ipn_notification_type": "POST"}

        response = requests.post(
            register_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json().get("ipn_id")

    except requests.exceptions.RequestException as e:
        logger.error(f"Pesapal IPN registration failed for URL {ipn_url}: {str(e)}")
        raise Exception("Failed to register IPN with Pesapal")


def submit_pesapal_order(order, auth_token, ipn_id):
    """
    Submit order to Pesapal with complete payload validation
    """
    try:
        order_url = f"{settings.PESAPAL_API_BASE}/api/Transactions/SubmitOrderRequest"

        first_paper = order.papers.first()
        if not first_paper:
            raise ValueError("Order has no papers associated")

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Build dynamic callback URL
        callback_url = f"{settings.PESAPAL_CALLBACK_URL}{order.id}/"

        payload = {
            "id": str(order.id),
            "currency": "USD",
            "amount": float(order.price),
            "description": f"Purchase of {first_paper.title}",
            "callback_url": callback_url,
            "notification_id": ipn_id,
            "billing_address": {
                "email_address": order.user.email,
                "first_name": order.user.first_name or "Customer",
                "last_name": order.user.last_name or "User",
            },
        }

        response = requests.post(
            order_url, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        logger.error(f"Pesapal order submission failed for order {order.id}: {str(e)}")
        raise Exception("Failed to submit order to Pesapal")


def handle_pesapal_checkout(order):
    try:
        auth_token = get_pesapal_auth_token()

        # Register IPN callback URL
        ipn_url = f"{settings.PESAPAL_IPN_BASE_URL}{order.id}/"
        ipn_id = register_pesapal_ipn(ipn_url, auth_token)

        # Submit order to Pesapal
        result = submit_pesapal_order(order, auth_token, ipn_id)

        # Save payment to database
        first_paper = order.papers.first()
        payment = Payment.objects.create(
            gateway="pesapal",
            external_id=result["order_tracking_id"],
            amount=order.price,
            currency="USD",
            description=f"Purchase of {first_paper.title}",
            status="created",
            order=order,
            customer_email=order.user.email,
        )

        # Create Pesapal-specific payment record
        PesapalPayment.objects.create(
            order=order,
            payment=payment,
            tracking_id=result["order_tracking_id"],
            merchant_reference=str(order.id),
            ipn_id=ipn_id,
            status="PENDING",
        )

        return {
            "checkout_url": result["redirect_url"],
            "order_id": order.id,
            "pesapal_order_id": result["order_tracking_id"],
        }
    except Exception as e:
        logger.error(f"Pesapal checkout failed: {str(e)}")
        raise Exception(f"Pesapal checkout failed: {str(e)}")
