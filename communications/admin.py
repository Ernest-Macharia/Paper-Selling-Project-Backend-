from django.contrib import admin

from .models import (
    ChatMessage,
    ContactMessage,
    CopyrightReport,
    EmailSubscriber,
    Notification,
)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "date_sent", "replied")
    search_fields = ("name", "email")
    list_editable = ("replied",)
    readonly_fields = ("name", "email", "message", "date_sent")
    fields = ("name", "email", "message", "date_sent", "replied", "admin_reply")


@admin.register(EmailSubscriber)
class EmailSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "date_subscribed")
    search_fields = ("email",)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "message", "timestamp", "room")
    search_fields = ("sender__username", "message", "room")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "timestamp")
    search_fields = ("user__username", "message")


@admin.register(CopyrightReport)
class CopyrightReportAdmin(admin.ModelAdmin):
    list_display = ("paper", "reason", "status", "created_at")
    list_filter = ("status", "reason")
    search_fields = ("paper__title", "details")
    readonly_fields = ("created_at", "updated_at")
    actions = ["mark_as_reviewed", "mark_as_dismissed"]

    def mark_as_reviewed(self, request, queryset):
        queryset.update(status="reviewed")

    mark_as_reviewed.short_description = "Mark selected reports as reviewed"

    def mark_as_dismissed(self, request, queryset):
        queryset.update(status="dismissed")

    mark_as_dismissed.short_description = "Mark selected reports as dismissed"
