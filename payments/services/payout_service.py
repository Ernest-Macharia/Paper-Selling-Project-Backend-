import logging

from django.conf import settings
from django.db import transaction
from django.utils.timezone import now

from mpesa_api.utils import get_mpesa_access_token, send_money_b2c
from payments.models import Wallet, WithdrawalRequest

logger = logging.getLogger(__name__)


def disburse_stripe(withdrawal):
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        transfer = stripe.Transfer.create(
            amount=int(withdrawal.amount * 100),  # in cents
            currency="usd",
            destination=withdrawal.destination,
            description=f"Withdrawal for {withdrawal.user.email}",
        )
        finalize_withdrawal(withdrawal, transfer.id)
        return {"status": "success", "transfer_id": transfer.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe payout failed: {e}")
        return {"status": "failed", "error": str(e)}


def disburse_paypal(withdrawal):
    import paypalrestsdk

    paypalrestsdk.configure(
        {
            "mode": settings.PAYPAL_MODE,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET,
        }
    )

    payout = paypalrestsdk.Payout(
        {
            "sender_batch_header": {
                "sender_batch_id": f"payout-{withdrawal.id}",
                "email_subject": "You have a payout!",
            },
            "items": [
                {
                    "recipient_type": "EMAIL",
                    "amount": {
                        "value": f"{withdrawal.amount:.2f}",
                        "currency": "USD",
                    },
                    "receiver": withdrawal.destination,
                    "note": "Thanks for using our platform!",
                    "sender_item_id": str(withdrawal.id),
                }
            ],
        }
    )

    if payout.create():
        batch_id = payout.batch_header.payout_batch_id
        finalize_withdrawal(withdrawal, batch_id)
        return {"status": "success", "transaction_reference": batch_id}
    else:
        logger.error(f"PayPal payout failed: {payout.error}")
        return {"status": "failed", "error": payout.error}


def disburse_mpesa(withdrawal):
    try:
        token = get_mpesa_access_token()
        result = send_money_b2c(
            phone_number=withdrawal.destination,
            amount=str(withdrawal.amount),
            access_token=token,
            occasion="Paper Earnings",
            remarks=f"Payout for {withdrawal.user.email}",
        )
        conversation_id = result.get("ConversationID")
        finalize_withdrawal(withdrawal, conversation_id)
        return {"status": "success", "transaction_id": conversation_id}
    except Exception as e:
        logger.error(f"M-Pesa payout failed: {e}")
        return {"status": "failed", "error": str(e)}


def resolve_destination(withdrawal):
    profile = getattr(withdrawal.user, "userpayoutprofile", None)
    if not profile:
        raise ValueError("Payout profile not found")

    if withdrawal.method == "stripe":
        return profile.stripe_account_id
    elif withdrawal.method == "paypal":
        return profile.paypal_email
    elif withdrawal.method == "mpesa":
        return profile.mpesa_phone
    else:
        raise ValueError("Unsupported payout method")


@transaction.atomic
def finalize_withdrawal(withdrawal, transaction_reference):
    withdrawal.status = "paid"
    withdrawal.paid_at = now()
    withdrawal.transaction_reference = transaction_reference
    withdrawal.save(update_fields=["status", "paid_at", "transaction_reference"])

    # Deduct from Wallet
    wallet = Wallet.objects.select_for_update().get(user=withdrawal.user)
    if wallet.balance < withdrawal.amount:
        raise ValueError("Insufficient wallet balance during payout finalization")
    wallet.balance -= withdrawal.amount
    wallet.save(update_fields=["balance"])

    logger.info(f"Withdrawal {withdrawal.id} finalized for {withdrawal.user.email}")


def disburse_withdrawal(withdrawal: WithdrawalRequest):
    if withdrawal.status != "approved":
        return {"status": "skipped", "reason": "Not approved"}

    try:
        withdrawal.destination = resolve_destination(withdrawal)
    except ValueError as e:
        logger.warning(f"Destination resolution failed: {e}")
        return {"status": "failed", "error": str(e)}

    if withdrawal.method == "stripe":
        return disburse_stripe(withdrawal)
    elif withdrawal.method == "paypal":
        return disburse_paypal(withdrawal)
    elif withdrawal.method == "mpesa":
        return disburse_mpesa(withdrawal)
    else:
        return {"status": "failed", "error": "Unsupported method"}
