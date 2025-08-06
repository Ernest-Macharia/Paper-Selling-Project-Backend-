from decimal import Decimal

from django.db import transaction

from payments.models import OrganizationAccount, Payment, Wallet


def update_payment_status(external_id, status, gateway):
    try:
        with transaction.atomic():
            payment = Payment.objects.get(external_id=external_id, gateway=gateway)
            payment.status = status
            payment.save(update_fields=["status"])

            if status == "completed":
                order = payment.order
                if order.status != "completed":
                    order.status = "completed"
                    order.save(update_fields=["status"])

                if not getattr(order, "credited", False):
                    credited_amount = order.price or payment.amount
                    if not credited_amount:
                        return

                    try:
                        seller = order.papers.first().author
                        seller_share = Decimal(credited_amount) * Decimal("0.65")
                        org_share = Decimal(credited_amount) * Decimal("0.35")

                        # Update Seller Wallet
                        seller_wallet, _ = Wallet.objects.get_or_create(user=seller)
                        seller_wallet.available_balance += seller_share
                        seller_wallet.total_earned += seller_share
                        seller_wallet.save()

                        # Update Org Account
                        org_account, _ = OrganizationAccount.objects.get_or_create(id=1)
                        org_account.available_balance += org_share
                        org_account.total_earnings += org_share
                        org_account.save()

                        # Mark credited
                        order.credited = True
                        order.save(update_fields=["credited"])

                    except Exception as e:
                        print(f"[Credit Error] Failed to credit order {order.id}: {e}")

    except Payment.DoesNotExist:
        print(f"[Payment Error] Payment with external_id={external_id} not found.")
