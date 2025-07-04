from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from payments.models import Wallet


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    is_seller = models.BooleanField(default=False)
    is_buyer = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"  # Use email as the username field
    REQUIRED_FIELDS = []  # Remove username requirement

    def save(self, *args, **kwargs):
        created = self.pk is None

        full_name = f"{self.first_name} {self.last_name}".strip()
        self.username = full_name.lower().replace(" ", "_")

        super().save(*args, **kwargs)

        # Create wallet only after user is saved for the first time
        if created:
            Wallet.objects.get_or_create(user=self)
