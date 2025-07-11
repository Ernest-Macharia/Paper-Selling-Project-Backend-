from datetime import timedelta, timezone

from celery import shared_task
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from payments.services.payout_service import disburse_withdrawal, resolve_destination
from users.models import User

from .models import OrganizationAccount, Payment, WithdrawalRequest

MIN_WITHDRAWAL_AMOUNT = 10


@receiver(post_save, sender=Payment)
def split_revenue(sender, instance, created, **kwargs):
    if not created or instance.status != "completed":
        return

    paper = instance.paper
    seller = paper.author

    org_share_percent = 35
    org_share = (instance.amount * org_share_percent) / 100
    seller_share = instance.amount - org_share

    wallet = seller.wallet
    wallet.available_balance += seller_share
    wallet.total_earned += seller_share
    wallet.save()

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
        return

    if wallet.available_balance >= MIN_WITHDRAWAL_AMOUNT:
        amount = wallet.available_balance

        WithdrawalRequest.objects.create(
            user=author,
            amount=amount,
            method=payout_profile.preferred_method,
            destination=resolve_destination(
                user=author, method=payout_profile.preferred_method
            ),
            status="pending",
        )

        wallet.available_balance = 0
        wallet.total_withdrawn += amount
        wallet.save()


@shared_task
def batch_process_withdrawals():
    now = timezone.now()

    if now.weekday() != 6:  # Sunday only
        return

    eligible_users = User.objects.filter(
        wallet__available_balance__gte=MIN_WITHDRAWAL_AMOUNT
    )

    for user in eligible_users:
        payout_profile = getattr(user, "userpayoutprofile", None)
        wallet = user.wallet

        recent_request = WithdrawalRequest.objects.filter(
            user=user,
            created_at__gte=now - timedelta(hours=24),
            status__in=["pending", "processing"],
        ).exists()

        if not payout_profile or not payout_profile.preferred_method or recent_request:
            continue

        amount = wallet.available_balance

        with transaction.atomic():
            withdrawal = WithdrawalRequest.objects.create(
                user=user,
                amount=amount,
                method=payout_profile.preferred_method,
                destination=resolve_destination(
                    user=user, method=payout_profile.preferred_method
                ),
                status="processing",
            )

            wallet.available_balance = 0
            wallet.total_withdrawn += amount
            wallet.save()

            disburse_withdrawal(withdrawal)
