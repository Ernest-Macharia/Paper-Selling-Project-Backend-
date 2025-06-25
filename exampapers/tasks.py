import os
from io import BytesIO
from random import sample

from celery import shared_task
from django.core.files.base import ContentFile
from PyPDF2 import PdfReader, PdfWriter

from .models import Paper


@shared_task
def generate_paper_preview(paper_id):

    try:
        paper = Paper.objects.get(id=paper_id)

        if not paper.file:
            return

        with paper.file.open("rb") as f:
            reader = PdfReader(f)
            total_pages = len(reader.pages)
            paper.page_count = total_pages

            if total_pages < 6:
                default_preview_path = os.path.join(
                    "media", "previews", "no_preview.pdf"
                )
                if os.path.exists(default_preview_path):
                    with open(default_preview_path, "rb") as default_file:
                        content = default_file.read()
                    paper.preview_file.save(
                        "no_preview.pdf", ContentFile(content), save=False
                    )
                paper.save(update_fields=["page_count", "preview_file"])
                return

            writer = PdfWriter()
            indices = sorted(sample(range(total_pages), min(4, total_pages)))
            for i in indices:
                writer.add_page(reader.pages[i])

            buffer = BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            preview_name = (
                os.path.splitext(os.path.basename(paper.file.name))[0] + "_preview.pdf"
            )
            paper.preview_file.save(
                preview_name, ContentFile(buffer.read()), save=False
            )
            paper.save()

    except Paper.DoesNotExist:
        pass
