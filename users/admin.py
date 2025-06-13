from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


class CustomUserAdmin(UserAdmin):
    ordering = ["email"]  # Change from 'username' to 'email'
    list_display = ("email", "first_name", "last_name", "is_seller", "is_buyer")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Roles", {"fields": ("is_seller", "is_buyer")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_seller", "is_buyer"),
            },
        ),
    )


admin.site.register(User, CustomUserAdmin)
