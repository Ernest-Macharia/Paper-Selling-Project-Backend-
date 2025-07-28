from django.core.management.base import BaseCommand

from exampapers.models import Paper


class Command(BaseCommand):
    help = "Publish all existing papers that have files and are not published yet."

    def handle(self, *args, **kwargs):
        papers = Paper.objects.filter(file__isnull=False).exclude(status="published")
        total = papers.count()

        papers.update(status="published")
        self.stdout.write(self.style.SUCCESS(f"✅ Published {total} papers"))
