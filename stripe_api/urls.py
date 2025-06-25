from django.urls import path

from . import views

urlpatterns = [
    path("create/", views.create_stripe_session, name="stripe-create-session"),
    path("webhook/", views.stripe_webhook, name="stripe-webhook"),
]
