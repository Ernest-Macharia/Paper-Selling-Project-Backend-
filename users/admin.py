from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomUserAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ("username", "email", "is_seller", "is_buyer")
    search_fields = ("username", "email")

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "avatar", "gender", "birth_year")},
        ),
        ("School Info", {"fields": ("school", "school_type", "course", "country")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Roles", {"fields": ("is_seller", "is_buyer")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "is_seller",
                    "is_buyer",
                ),
            },
        ),
    )


admin.site.register(User, CustomUserAdmin)
