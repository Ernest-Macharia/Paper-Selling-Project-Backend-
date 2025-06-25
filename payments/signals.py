# payments/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OrganizationAccount, Payment, WithdrawalRequest


@receiver(post_save, sender=Payment)
def split_revenue(sender, instance, created, **kwargs):
    if not created or instance.status != "completed":
        return

    paper = instance.paper
    seller = paper.author

    org_share_percent = 30
    org_share = (instance.amount * org_share_percent) / 100
    seller_share = instance.amount - org_share

    # Update seller balance
    wallet = seller.wallet  # Assuming OneToOne
    wallet.available_balance += seller_share
    wallet.total_earned += seller_share
    wallet.save()

    # Update org account
    org_account, _ = OrganizationAccount.objects.get_or_create(id=1)
    org_account.total_earnings += org_share
    org_account.available_balance += org_share
    org_account.save()


@receiver(post_save, sender=Payment)
def auto_create_withdrawal(sender, instance, created, **kwargs):
    if not created or instance.status != "completed":
        return

    wallet = instance.paper.author.wallet
    if wallet.available_balance >= 100:  # e.g., auto payout at $100
        WithdrawalRequest.objects.create(
            user=instance.paper.author,
            amount=wallet.available_balance,
            method=instance.paper.author.userpayoutprofile.preferred_method,
            status="pending",
        )
        wallet.available_balance = 0
        wallet.total_withdrawn += wallet.available_balance
        wallet.save()
