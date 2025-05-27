from django.urls import path

from . import views
from .views import lipa_na_mpesa_direct, mpesa_callback


urlpatterns = [
    path('lipa-online/', lipa_na_mpesa_direct, name='lipa_online'),
    path('callback/',    mpesa_callback,     name='mpesa_callback'),
    # path('access/token', views.getAccessToken, name='get_mpesa_access_token'),
    # path('online/lipa', views.lipa_na_mpesa_online, name='lipa_na_mpesa'),
    # path('c2b/register', views.register_urls, name="register_mpesa_validation"),
    # path('c2b/confirmation', views.confirmation, name="confirmation"),
    # path('c2b/validation', views.validation, name="validation"),
    # path('c2b/callback', views.call_back, name="call_back"),
]