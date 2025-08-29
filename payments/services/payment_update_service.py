import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
from django.utils.timezone import now

from payments.models import OrganizationAccount, Payment, Wallet

logger = logging.getLogger(__name__)


def update_payment_status(external_id, status, gateway):
    try:
        with transaction.atomic():
            payment = Payment.objects.select_related("order").get(
                external_id=external_id, gateway=gateway
            )
            order = payment.order

            # Update payment status
            payment.status = status
            payment.save(update_fields=["status"])
            logger.info(f"[Payment Update] Payment {payment.id} set to {status}")

            if status == "completed":
                if order.status != "completed":
                    order.status = "completed"
                    order.save(update_fields=["status"])
                    logger.info(f"[Order Update] Order {order.id} set to completed")
                    send_payment_success_email(
                        order, order.user, list(order.papers.all())
                    )

                credited_amount = order.price or payment.amount
                if not credited_amount:
                    logger.warning(
                        f"[Credit Skipped] No amount found for order {order.id}"
                    )
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
                    logger.info(
                        f"[Wallet Update] Seller {seller.id} credited {seller_share}"
                    )

                    # Update Org Account
                    org_account, _ = OrganizationAccount.objects.get_or_create(id=1)
                    org_account.available_balance += org_share
                    org_account.total_earnings += org_share
                    org_account.save()
                    logger.info(f"[Org Update] Org credited {org_share}")

                    # Mark credited
                    if not getattr(order, "credited", False):
                        order.credited = True
                        order.save(update_fields=["credited"])
                        logger.info(
                            f"[Credit Flag] Order {order.id} marked as credited"
                        )

                except Exception as e:
                    logger.error(
                        f"[Credit Error] Failed to credit order {order.id}: {e}"
                    )

    except Payment.DoesNotExist:
        logger.error(
            f"[Payment Error] Payment with external_id={external_id}, gateway={gateway} not found."
        )


def send_payment_success_email(order, user, papers):
    """Send a payment success email with download links for purchased papers"""

    # Build download URLs for each purchased paper
    paper_downloads = [
        {
            "title": paper.title,
            "download_url": f"{settings.BASE_URL}/api/exampapers/papers/{paper.id}/download/",
        }
        for paper in papers
    ]

    context = {
        "user": user,
        "order": order,
        "papers": paper_downloads,
        "year": now().year,
    }

    subject = "Payment Successful - Download Your Papers"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    html_content = render_to_string("emails/payment_success_email.html", context)
    text_content = (
        f"Hi {user.username},\n\n"
        f"Your payment was successful. You can download your purchased papers below:\n\n"
        + "\n".join([f"- {p['title']}: {p['download_url']}" for p in paper_downloads])
        + "\n\nThank you for using GradesWorld!"
    )

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
