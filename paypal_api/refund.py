import paypalrestsdk
from django.conf import settings

paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


def process_paypal_refund(payment):
    try:
        sale = None
        payment_obj = paypalrestsdk.Payment.find(payment.paypal_order_id)
        if payment_obj and payment_obj.transactions:
            related_resources = payment_obj.transactions[0].related_resources
            sale = related_resources[0].sale.id if related_resources else None

        if not sale:
            return {"status": "failed", "error": "Sale ID not found"}

        refund = paypalrestsdk.Refund(
            {"amount": {"total": f"{payment.amount:.2f}", "currency": payment.currency}}
        )

        sale_obj = paypalrestsdk.Sale.find(sale)
        refund_response = sale_obj.refund(refund)

        if refund_response.success():
            return {"status": "success", "refund_id": refund_response.id}
        else:
            return {"status": "failed", "error": refund_response.error}

    except paypalrestsdk.ResourceNotFound as e:
        return {"status": "failed", "error": str(e)}
