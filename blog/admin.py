# blog/admin.py
from django.contrib import admin

from .models import BlogPost, Category, Comment, Like, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    readonly_fields = ("user", "content", "created_at")
    can_delete = True


class LikeInline(admin.TabularInline):
    model = Like
    extra = 0
    readonly_fields = ("user", "created_at")
    can_delete = True


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "is_published", "created_at")
    list_filter = ("is_published", "category", "tags")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [CommentInline, LikeInline]
    autocomplete_fields = ["category", "tags"]
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Post Info",
            {
                "fields": (
                    "title",
                    "slug",
                    "author",
                    "category",
                    "tags",
                    "image",
                    "is_published",
                )
            },
        ),
        ("Content", {"fields": ("content",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "content", "created_at")
    list_filter = ("created_at", "post")
    search_fields = ("content", "user__username", "post__title")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "post__title")
