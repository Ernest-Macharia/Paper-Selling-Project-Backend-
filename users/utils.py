# your_app/utils.py
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.timezone import now

User = get_user_model()


def send_activation_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    activation_link = f"{settings.BASE_URL}/activate/{uid}/{token}/"

    html_message = render_to_string(
        "emails/activation_email_template.html",
        {
            "user": user,
            "activation_link": activation_link,
            "current_year": now().year,
        },
    )

    subject = "Activate Your GradesWorld Account"
    message = f"Hi {user.username},\n\nPlease activate your account by\
        clicking the link below:\n\n{activation_link}\n\nThank you!"
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently=False,
        html_message=html_message,
    )
