from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, unified_checkout

router = DefaultRouter()
router.register(r"payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("checkout/", unified_checkout, name="checkout-initiate"),
]
