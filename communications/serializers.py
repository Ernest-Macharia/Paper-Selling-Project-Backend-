from rest_framework import serializers

from .models import ChatMessage, ContactMessage, CopyrightReport, EmailSubscriber


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = "__all__"


class EmailSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSubscriber
        fields = "__all__"


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = "__all__"


class CopyrightReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CopyrightReport
        fields = [
            "id",
            "paper",
            "reason",
            "details",
            "contact_email",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]
