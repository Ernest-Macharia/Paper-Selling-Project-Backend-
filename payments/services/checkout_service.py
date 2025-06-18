from mpesa_api.checkout import handle_mpesa_checkout
from paypal_api.checkout import handle_paypal_checkout
from stripe_api.checkout import handle_stripe_checkout


def handle_checkout(payment_method, order, phone_number=None):
    if payment_method == "mpesa":
        return handle_mpesa_checkout(order, phone_number=phone_number)
    elif payment_method == "paypal":
        return handle_paypal_checkout(order)
    elif payment_method == "stripe":
        return handle_stripe_checkout(order)
    else:
        raise ValueError("Unsupported payment gateway")
