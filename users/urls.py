from django.urls import path

from .views import (
    CurrentUserView,
    CustomLoginView,
    RegisterUserView,
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
]
