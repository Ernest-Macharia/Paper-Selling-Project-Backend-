from django.urls import path

from .views import paypal_capture, paypal_create

urlpatterns = [
    path("create/", paypal_create, name="paypal-create"),
    path("capture/", paypal_capture, name="paypal-capture"),
]
