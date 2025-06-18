from mpesa_api.models import MpesaPayment
from mpesa_api.utils import initiate_stk_push
from payments.models import Payment


def handle_mpesa_checkout(data):
    phone = data.get("phone_number")
    if not phone:
        raise Exception("Phone number required for Mpesa")

    amount = int(round(float(data["amount"])))

    resp = initiate_stk_push(phone, amount)

    merchant_req_id = resp.get("MerchantRequestID")
    checkout_req_id = resp.get("CheckoutRequestID")

    # Create unified payment record
    payment = Payment.objects.create(
        gateway="mpesa",
        external_id=checkout_req_id,
        amount=data["amount"],
        currency=data["currency"],
        customer_email=data.get("email"),
        description=data.get("description"),
        status="pending",
    )

    MpesaPayment.objects.create(
        payment=payment,
        merchant_request_id=merchant_req_id,
        checkout_request_id=checkout_req_id,
        # phone_number=phone,
    )

    return {"checkout_id": checkout_req_id, "response": resp}
