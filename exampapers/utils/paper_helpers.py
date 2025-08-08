import logging
import os
from io import BytesIO
from typing import BinaryIO, Optional, Union

from django.core.files.base import ContentFile
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)
DEFAULT_WATERMARK_TEXT = "Gradesworld.com"


def set_page_count(paper) -> None:
    """Set the number of pages for a Paper.

    Args:
        paper: The Paper model instance to update.

    Raises:
        RuntimeError: If the page count cannot be determined.
    """
    if not paper.file:
        return

    try:
        with paper.file.open("rb") as f:
            reader = PdfReader(f)
            paper.page_count = len(reader.pages)
            paper.save(update_fields=["page_count"])
    except Exception as e:
        raise RuntimeError(f"Failed to set page count: {e}")


def generate_preview(self) -> None:
    """Generate a responsive preview PDF optimized for all devices using pypdf."""
    if not self.file:
        logger.warning(
            f"No file found for paper {self.id}, skipping preview generation"
        )
        return

    try:
        with self.file.open("rb") as f:
            reader = PdfReader(f)
            total_pages = len(reader.pages)

            if total_pages < 6:
                logger.info(
                    f"Paper {self.id} has only {total_pages} pages, skipping preview"
                )
                return

            preview_pages = 1 if total_pages < 10 else (2 if total_pages < 50 else 3)

            writer = PdfWriter()

            for i in range(min(preview_pages, total_pages)):
                page = reader.pages[i]
                orig_width = float(page.mediabox.width)
                orig_height = float(page.mediabox.height)
                scale = min((595 - 40) / orig_width, (842 - 40) / orig_height)

                # Create new blank page
                writer.add_blank_page(width=595, height=842)
                # Get the last added page
                new_page = writer.pages[-1]

                # Merge with transformation
                new_page.merge_transformed_page(
                    page,
                    (
                        scale,
                        0,
                        0,
                        scale,
                        (595 - orig_width * scale) / 2,
                        (842 - orig_height * scale) / 2,
                    ),
                )

            # Save preview to BytesIO buffer first
            pdf_buffer = BytesIO()
            writer.write(pdf_buffer)
            pdf_buffer.seek(0)

            # Save to model field
            preview_name = f"previews/{self.id}_{os.path.basename(self.file.name)}"
            self.preview_file.save(
                preview_name, ContentFile(pdf_buffer.getvalue()), save=False
            )

            # Generate preview image from the buffer
            self._generate_preview_image(pdf_buffer)

            self.save(update_fields=["preview_file", "preview_image"])

    except Exception as e:
        logger.error(f"Failed to generate preview for paper {self.id}: {str(e)}")
        raise


def _generate_preview_image(self, pdf_buffer: BytesIO) -> None:
    """Generate a fallback image preview for mobile devices."""
    try:
        # Convert first page to image
        images = convert_from_bytes(
            pdf_buffer.getvalue(), dpi=100, first_page=1, last_page=1, fmt="jpeg"
        )

        if images:
            img_buffer = BytesIO()
            images[0].save(img_buffer, format="JPEG", quality=85)
            img_buffer.seek(0)

            preview_image_name = (
                os.path.splitext(os.path.basename(self.file.name))[0] + "_preview.jpg"
            )
            self.preview_image.save(
                preview_image_name, ContentFile(img_buffer.getvalue()), save=False
            )
    except Exception as e:
        logger.warning(f"Couldn't generate image preview: {str(e)}")


def create_watermark(text: str = DEFAULT_WATERMARK_TEXT) -> PdfReader:
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFillAlpha(0.2)
    can.setFont("Helvetica", 60)
    can.setFillColorRGB(0.3, 0.3, 0.3)
    width, height = letter
    can.drawCentredString(width / 2, 30, text)
    can.save()
    packet.seek(0)
    return PdfReader(packet)


def add_watermark_to_pdf(
    input_file: Union[BinaryIO, BytesIO], output_stream: Optional[BytesIO] = None
) -> BytesIO:
    output_stream = output_stream or BytesIO()
    watermark = create_watermark()
    reader = PdfReader(input_file)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i == 0:  # only watermark first page
            page.merge_page(watermark.pages[0])
        writer.add_page(page)

    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream
