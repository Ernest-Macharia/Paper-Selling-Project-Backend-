from django.urls import path

from .views import (
    CurrentUserView,
    CustomLoginView,
    PasswordResetConfirmView,
    RegisterUserView,
    RequestPasswordResetView,
    UpdateUserDetailsView,
    UserListView,
)

urlpatterns = [
    path("register/", RegisterUserView.as_view(), name="register"),
    path("login/", CustomLoginView.as_view(), name="custom_login"),
    path("all_users/", UserListView.as_view(), name="user_list"),
    path("current-user/", CurrentUserView.as_view(), name="current_user"),
    path(
        "current-user/update/",
        UpdateUserDetailsView.as_view(),
        name="current_user_update",
    ),
    path(
        "request-password-reset/",
        RequestPasswordResetView.as_view(),
        name="request-password-reset",
    ),
    path(
        "reset-password-confirm/",
        PasswordResetConfirmView.as_view(),
        name="reset-password",
    ),
]
