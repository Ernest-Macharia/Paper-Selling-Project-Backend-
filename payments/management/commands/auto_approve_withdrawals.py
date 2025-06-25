# payments/management/commands/process_withdrawals.py

import logging

from django.core.management.base import BaseCommand

from payments.models import WithdrawalRequest

# from payments.services.payout_service import disburse_withdrawal

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process all approved withdrawal requests"

    def handle(self, *args, **options):
        withdrawals = WithdrawalRequest.objects.filter(status="approved")
        self.stdout.write(f"Processing {withdrawals.count()} approved withdrawals")

        # for withdrawal in withdrawals:
        #     result = disburse_withdrawal(withdrawal)
        # self.stdout.write(
        #     f"Withdrawal {withdrawal.id} ->
        # {result['status']} or {result.get('error') or result.get(
        #         'transaction_id') or result.get(
        #             'transfer_id') or result.get(
        #                 'transaction_reference')}"
        # )
