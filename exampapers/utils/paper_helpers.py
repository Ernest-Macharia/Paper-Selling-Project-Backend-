import os
from io import BytesIO

from django.core.files.base import ContentFile
from PyPDF2 import PdfReader, PdfWriter


def set_page_count(paper):
    """Set the number of pages for a Paper."""
    if not paper.file:
        return

    try:
        with paper.file.open("rb") as f:
            reader = PdfReader(f)
            paper.page_count = len(reader.pages)
            paper.save(update_fields=["page_count"])
    except Exception as e:
        raise RuntimeError(f"Failed to set page count: {e}")


def generate_preview(paper):
    """Generate a preview PDF with the first 4 pages or fallback to a default preview."""
    if not paper.file:
        return

    try:
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
                        paper.preview_file.save(
                            "no_preview.pdf",
                            ContentFile(default_file.read()),
                            save=False,
                        )
                paper.save(update_fields=["page_count", "preview_file"])
                return

            # Take the first 4 pages (or fewer if document has less than 4 pages)
            writer = PdfWriter()
            for i in range(min(4, total_pages)):
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
            paper.save(update_fields=["page_count", "preview_file"])

    except Exception as e:
        raise RuntimeError(f"Preview generation failed: {e}")
