import logging

from paypal_api.checkout import handle_paypal_checkout
from paystack.checkout import handle_paystack_checkout
from pesapal.checkout import handle_pesapal_checkout
from stripe_api.checkout import handle_stripe_checkout

logger = logging.getLogger(__name__)


def handle_checkout(provider, order):
    if provider == "paypal":
        return handle_paypal_checkout(order)
    elif provider == "stripe":
        return handle_stripe_checkout(order)
    elif provider == "paystack":
        return handle_paystack_checkout(order)
    elif provider == "pesapal":
        return handle_pesapal_checkout(order)
    else:
        raise ValueError("Unsupported payment provider")
