from django.urls import path
from .views import paypal_create, paypal_capture

urlpatterns = [
    path('create/',  paypal_create,  name='paypal-create'),
    path('capture/', paypal_capture, name='paypal-capture'),
]
