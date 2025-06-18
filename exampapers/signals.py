# papers/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Paper
from .tasks import generate_paper_preview


@receiver(post_save, sender=Paper)
def generate_preview_after_upload(sender, instance, created, **kwargs):
    if created:
        generate_paper_preview.delay(instance.id)
