from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_stripe_session, name='stripe-create-session'),
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
    path('stripe-payment-success/', views.stripe_payment_success, name='stripe-payment-success'),
    path('stripe-payment-cancelled/', views.stripe_payment_cancelled, name='stripe-payment-cancelled'),
]