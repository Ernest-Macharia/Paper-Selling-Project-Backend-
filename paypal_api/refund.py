import logging

import paypalrestsdk
from django.conf import settings

logger = logging.getLogger(__name__)

paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


def process_paypal_refund(payment):
    try:
        payment_obj = paypalrestsdk.Payment.find(payment.external_id)
        sale_id = (
            payment_obj.transactions[0].related_resources[0].sale.id
            if payment_obj.transactions
            and payment_obj.transactions[0].related_resources
            else None
        )

        if not sale_id:
            logger.error("Refund failed: Sale ID not found")
            return {"status": "failed", "error": "Sale ID not found"}

        sale = paypalrestsdk.Sale.find(sale_id)
        refund_response = sale.refund(
            {"amount": {"total": f"{payment.amount:.2f}", "currency": payment.currency}}
        )

        if refund_response.success():
            logger.info("Refund successful: %s", refund_response.id)
            return {"status": "success", "refund_id": refund_response.id}
        else:
            logger.error("Refund failed: %s", refund_response.error)
            return {"status": "failed", "error": refund_response.error}

    except paypalrestsdk.ResourceNotFound as e:
        logger.error("Refund exception: %s", str(e))
        return {"status": "failed", "error": str(e)}
