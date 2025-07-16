from django.core.management.base import BaseCommand

from exampapers.models import Paper
from exampapers.tasks import generate_paper_preview


class Command(BaseCommand):
    help = "Generate missing previews for all existing papers"

    def handle(self, *args, **kwargs):
        papers = Paper.objects.filter(preview_file="", file__isnull=False)
        self.stdout.write(f"Found {papers.count()} papers without preview.")

        for paper in papers:
            generate_paper_preview.delay(paper.id)
            self.stdout.write(f"Dispatched preview task for paper: {paper.title}")
