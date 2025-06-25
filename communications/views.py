from django.conf import settings
from django.core.mail import send_mail
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ContactMessage, EmailSubscriber
from .serializers import ContactMessageSerializer, EmailSubscriberSerializer


class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()

        # Send email to admin
        subject = f"New Contact Message from {instance.name}"
        message = f"Name: {instance.name}\nEmail: \
            {instance.email}\n\nMessage:\n{instance.message}"
        admin_email = settings.DEFAULT_FROM_EMAIL

        send_mail(
            subject,
            message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=False,
        )


class EmailSubscriberCreateView(generics.CreateAPIView):
    queryset = EmailSubscriber.objects.all()
    serializer_class = EmailSubscriberSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        instance = serializer.save()
        subject = "Thank you for subscribing to GradesWorld!"
        message = "You've been subscribed to our email list. \
        Stay tuned for updates and resources!"

        send_mail(
            subject,
            message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[instance.email],
            fail_silently=False,
        )


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
            return Response(
                {"detail": "Unsubscribed successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except EmailSubscriber.DoesNotExist:
            return Response(
                {"detail": "Email not found."}, status=status.HTTP_404_NOT_FOUND
            )
