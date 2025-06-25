from django.contrib import admin

from .models import ContactMessage, EmailSubscriber


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "date_sent")
    search_fields = ("name", "email")


@admin.register(EmailSubscriber)
class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "date_subscribed")
    search_fields = ("email",)
