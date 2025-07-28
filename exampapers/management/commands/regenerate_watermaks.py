import os

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from exampapers.models import Paper
from exampapers.utils.paper_helpers import add_watermark_to_pdf


class Command(BaseCommand):
    help = "Regenerate watermark for all existing papers"

    def handle(self, *args, **kwargs):
        papers = Paper.objects.filter(file__isnull=False)

        for paper in papers:
            self.stdout.write(f"Processing: {paper.title}")

            # Check for missing files
            if not paper.file.storage.exists(paper.file.name):
                self.stderr.write(
                    f"Skipping {paper.title}: file not found at {paper.file.path}"
                )
                continue

            # Check file extension
            ext = os.path.splitext(paper.file.name)[1].lower()
            if ext != ".pdf":
                self.stderr.write(
                    f"Skipping {paper.title}: unsupported file type '{ext}'"
                )
                continue

            try:
                with paper.file.open("rb") as f:
                    buf = add_watermark_to_pdf(f)

                original_name = os.path.basename(paper.file.name)

                if not original_name.startswith("watermarked_"):
                    new_name = f"watermarked_{original_name}"
                else:
                    new_name = original_name

                paper.file.save(new_name, ContentFile(buf.getvalue()), save=True)
                self.stdout.write(f"Watermark added to {paper.title}")

            except Exception as e:
                self.stderr.write(f"Error processing {paper.title}: {str(e)}")
