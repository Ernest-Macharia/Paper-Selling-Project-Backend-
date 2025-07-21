from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from exampapers.models import Paper

User = get_user_model()


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    date_sent = models.DateTimeField(auto_now_add=True)
    replied = models.BooleanField(default=False)
    admin_reply = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Message from {self.name} - {self.email}"


class EmailSubscriber(models.Model):
    email = models.EmailField(unique=True)
    date_subscribed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class ChatMessage(models.Model):
    sender = models.ForeignKey(
        User, related_name="sent_messages", on_delete=models.CASCADE
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    room = models.CharField(max_length=255)


class Notification(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="communication_notifications"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)


class CopyrightReport(models.Model):
    REASON_CHOICES = [
        ("copyright", "Copyright infringement"),
        ("plagiarism", "Plagiarism"),
        ("unauthorized", "Unauthorized distribution"),
        ("other", "Other"),
    ]

    paper = models.ForeignKey(
        Paper, on_delete=models.CASCADE, related_name="copyright_reports"
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    details = models.TextField()
    contact_email = models.EmailField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("reviewed", "Reviewed"),
            ("dismissed", "Dismissed"),
        ],
        default="pending",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Report on {self.paper.title} ({self.get_reason_display()})"
