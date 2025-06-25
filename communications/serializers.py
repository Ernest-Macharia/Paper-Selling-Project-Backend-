from rest_framework import serializers

from .models import ContactMessage, EmailSubscriber


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = "__all__"


class EmailSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSubscriber
        fields = "__all__"
