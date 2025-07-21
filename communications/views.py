from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import ChatMessage, ContactMessage, CopyrightReport, EmailSubscriber
from .serializers import (
    ChatMessageSerializer,
    ContactMessageSerializer,
    CopyrightReportSerializer,
    EmailSubscriberSerializer,
)


class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()

        # Send email to admin
        subject = f"New Contact Message from {instance.name}"
        message = f"Name: {instance.name}\nEmail: {instance.email}\n\nMessage:\n{instance.message}"
        admin_email = settings.DEFAULT_FROM_EMAIL

        send_mail(
            subject,
            message,
            from_email=admin_email,
            recipient_list=[admin_email],
            fail_silently=False,
        )


class EmailSubscriberCreateView(generics.CreateAPIView):
    queryset = EmailSubscriber.objects.all()
    serializer_class = EmailSubscriberSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()
        subject = "🎉 Thank You for Subscribing to GradesWorld!"
        recipient = instance.email
        from_email = settings.DEFAULT_FROM_EMAIL

        html_content = render_to_string(
            "emails/subscription_email.html", {"email": recipient}
        )
        text_content = (
            "Thank you for subscribing to GradesWorld! Stay tuned for updates."
        )

        msg = EmailMultiAlternatives(subject, text_content, from_email, [recipient])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


class EmailUnsubscribeView(generics.DestroyAPIView):
    queryset = EmailSubscriber.objects.all()
    permission_classes = [AllowAny]

    def delete(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            subscriber = EmailSubscriber.objects.get(email=email)
            subscriber.delete()

            subject = "📭 You’ve Unsubscribed from GradesWorld"
            from_email = settings.DEFAULT_FROM_EMAIL
            html_content = render_to_string(
                "emails/unsubscription_email.html", {"email": email}
            )
            text_content = "You've been unsubscribed from GradesWorld."

            msg = EmailMultiAlternatives(subject, text_content, from_email, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            return Response(
                {"detail": "Unsubscribed successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except EmailSubscriber.DoesNotExist:
            return Response(
                {"detail": "Email not found."}, status=status.HTTP_404_NOT_FOUND
            )


class ChatHistoryView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        room = self.kwargs["room"]
        return ChatMessage.objects.filter(room=room).order_by("timestamp")


class CopyrightReportCreateView(generics.CreateAPIView):
    queryset = CopyrightReport.objects.all()
    serializer_class = CopyrightReportSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(
            reporter=self.request.user if self.request.user.is_authenticated else None
        )
