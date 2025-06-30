import requests
from django.conf import settings

from payments.models import Payment
from paypal_api.models import PayPalPayment

DEFAULT_TIMEOUT = 30


def get_paypal_access_token():
    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v1/oauth2/token",
        auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_CLIENT_SECRET),
        headers={"Accept": "application/json"},
        data={"grant_type": "client_credentials"},
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def handle_paypal_checkout(order):
    first_paper = order.papers.first()
    if not first_paper:
        raise ValueError("Order has no papers associated")

    base_url = settings.BASE_URL
    access_token = get_paypal_access_token()

    data = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "amount": {"currency_code": "USD", "value": f"{order.price:.2f}"},
                "description": f"Purchase of {first_paper.title}",
            }
        ],
        "application_context": {
            "return_url": f"{base_url}/payment/success?order_id={order.id}",
            "cancel_url": settings.PAYPAL_CANCEL_URL,
        },
    }

    response = requests.post(
        f"{settings.PAYPAL_API_BASE}/v2/checkout/orders",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        json=data,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    approval_url = next(
        (link["href"] for link in result["links"] if link["rel"] == "approve"), None
    )
    if not approval_url:
        raise Exception("Approval URL not found in PayPal response")

    # Save to DB
    payment = Payment.objects.create(
        gateway="paypal",
        external_id=result["id"],
        amount=order.price,
        currency="USD",
        description=f"Purchase of {first_paper.title}",
        status="created",
        order=order,
        customer_email=order.user.email,
    )

    PayPalPayment.objects.create(payment=payment, paypal_order_id=result["id"])

    return {
        "checkout_url": approval_url,
        "order_id": order.id,
        "session_id": result["id"],
    }
