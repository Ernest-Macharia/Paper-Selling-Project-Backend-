from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from payments.models import WithdrawalRequest

User = get_user_model()


@shared_task
def send_withdrawal_email_async(user_id, withdrawal_id, template_name, subject):
    user = User.objects.get(id=user_id)
    withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id)

    html_content = render_to_string(
        f"emails/{template_name}",
        {
            "user": user,
            "withdrawal": withdrawal,
            "year": datetime.now().year,
        },
    )
    text_content = "This is a withdrawal notification from GradesWorld."

    msg = EmailMultiAlternatives(
        subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email]
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
