from payments.models import Payment


def update_payment_status(external_id, status, gateway):
    try:
        payment = Payment.objects.get(external_id=external_id, gateway=gateway)
        payment.status = status
        payment.save(update_fields=["status"])

        if status == "completed":
            order = payment.order
            order.status = "completed"
            order.save(update_fields=["status"])
    except Payment.DoesNotExist:
        pass
