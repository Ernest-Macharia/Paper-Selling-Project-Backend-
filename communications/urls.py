from django.urls import path

from .views import (
    ContactMessageCreateView,
    EmailSubscriberCreateView,
    EmailUnsubscribeView,
)

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-message"),
    path("subscribe/", EmailSubscriberCreateView.as_view(), name="email-subscribe"),
    path("unsubscribe/", EmailUnsubscribeView.as_view(), name="email-unsubscribe"),
]
