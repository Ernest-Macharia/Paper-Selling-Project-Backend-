from django.urls import path

from . import views
from .views import paypal_capture, paypal_create

urlpatterns = [
    path("create/", paypal_create, name="paypal-create"),
    path("capture/", paypal_capture, name="paypal-capture"),
    path(
        "paypal-payment-success/",
        views.paypal_payment_success,
        name="paypal-payment-success",
    ),
    path(
        "paypal-payment-cancelled/",
        views.paypal_payment_cancelled,
        name="paypal-payment-cancelled",
    ),
]
