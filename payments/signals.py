# payments/signals.py

from datetime import timedelta, timezone

from celery import shared_task
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.services.payout_service import disburse_withdrawal
from users.models import User

from .models import OrganizationAccount, Payment, WithdrawalRequest

MIN_WITHDRAWAL_AMOUNT = 10
WITHDRAWAL_COOLDOWN_DAYS = 7


@receiver(post_save, sender=Payment)
def split_revenue(sender, instance, created, **kwargs):
    if not created or instance.status != "completed":
        return

    paper = instance.paper
    seller = paper.author

    org_share_percent = 35
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

    author = instance.paper.author
    wallet = author.wallet
    payout_profile = getattr(author, "userpayoutprofile", None)

    if not payout_profile or not payout_profile.preferred_method:
        return  # No payout method set

    if wallet.available_balance >= 10:  # Set to $10 threshold
        amount_to_withdraw = wallet.available_balance

        WithdrawalRequest.objects.create(
            user=author,
            amount=amount_to_withdraw,
            method=payout_profile.preferred_method,
            status="pending",
        )

        wallet.available_balance = 0
        wallet.total_withdrawn += amount_to_withdraw
        wallet.save()


@shared_task
def batch_process_withdrawals():
    now = timezone.now()

    # Only process on Sundays (00:00 to 23:59)
    if now.weekday() != 6:
        return  # 6 = Sunday

    # Fetch users eligible for payout (balance >= $10)
    eligible_users = User.objects.filter(wallet__available_balance__gte=10)

    for user in eligible_users:
        payout_profile = getattr(user, "userpayoutprofile", None)
        wallet = user.wallet

        # Prevent duplicate payout requests within the last 24 hours
        recent_request = WithdrawalRequest.objects.filter(
            user=user,
            created_at__gte=now - timedelta(hours=24),
            status__in=["pending", "processing"],
        ).exists()

        if not payout_profile or not payout_profile.preferred_method or recent_request:
            continue

        amount = wallet.available_balance

        with transaction.atomic():
            # Create withdrawal request
            withdrawal = WithdrawalRequest.objects.create(
                user=user,
                amount=amount,
                method=payout_profile.preferred_method,
                status="processing",
            )

            # Update wallet balances
            wallet.total_withdrawn += amount
            wallet.available_balance = 0
            wallet.save()

            # Call disbursement logic
            disburse_withdrawal(withdrawal)
