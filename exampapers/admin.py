from django.contrib import admin

from exampapers.tasks import generate_paper_preview

from .models import (
    Category,
    Course,
    Notification,
    Order,
    Paper,
    Review,
    School,
    Statistics,
    Wishlist,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "category",
        "course",
        "price",
        "upload_date",
        "downloads",
        "earnings",
    )
    search_fields = (
        "title",
        "author__username",
        "author__email",
        "category__name",
        "course__name",
    )
    list_filter = ("upload_date", "category", "course", "earnings")
    readonly_fields = ("downloads", "earnings")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        generate_paper_preview.delay(obj.id)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("paper", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("paper__title", "user__email")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "list_papers", "price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "papers__title")

    def list_papers(self, obj):
        return ", ".join([paper.title for paper in obj.papers.all()])

    list_papers.short_description = "Papers"


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user", "paper", "added_at")
    search_fields = ("user__email", "paper__title")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "timestamp")
    list_filter = ("is_read",)
    search_fields = ("user__email", "message")


@admin.register(Statistics)
class StatisticsAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "total_papers",
        "total_downloads",
        "total_earnings",
        "total_users",
    )
    list_filter = ("date",)
    ordering = ["-date"]
