from django.urls import path, re_path

from communications import consumers

from .views import (
    ContactMessageCreateView,
    CopyrightReportCreateView,
    EmailSubscriberCreateView,
    EmailUnsubscribeView,
)

urlpatterns = [
    path("contact/", ContactMessageCreateView.as_view(), name="contact-message"),
    path("subscribe/", EmailSubscriberCreateView.as_view(), name="email-subscribe"),
    path("unsubscribe/", EmailUnsubscribeView.as_view(), name="email-unsubscribe"),
    path(
        "copyright-reports/",
        CopyrightReportCreateView.as_view(),
        name="copyright-reports",
    ),
    re_path(r"ws/chat/(?P<room_name>\w+)/$", consumers.ChatConsumer.as_asgi()),
]
