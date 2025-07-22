import logging
import os
from io import BytesIO
from typing import BinaryIO, Optional, Union

from django.core.files.base import ContentFile
from PyPDF2 import PdfReader, PdfWriter
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
    """Generate a preview PDF containing the first 5 pages of the document."""
    if not self.file:
        return

    try:
        with self.file.open("rb") as f:
            reader = PdfReader(f)
            writer = PdfWriter()

            # Add first 5 pages (or fewer if shorter)
            for page in reader.pages[:5]:
                writer.add_page(page)

            # Write to memory
            buffer = BytesIO()
            writer.write(buffer)
            buffer.seek(0)

            # Save to preview_file
            preview_name = (
                os.path.splitext(os.path.basename(self.file.name))[0] + "_preview.pdf"
            )
            self.preview_file.save(
                preview_name, ContentFile(buffer.getvalue()), save=False
            )
            self.save(update_fields=["preview_file"])
    except Exception as e:
        logger.error(f"Error generating preview for paper {self.id}: {str(e)}")


def create_watermark(text: str = DEFAULT_WATERMARK_TEXT) -> PdfReader:
    """Create a PDF watermark with the specified text.

    Args:
        text: The text to use for the watermark.

    Returns:
        PdfReader: A PDF reader containing the watermark.
    """
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)

    # Watermark styling
    can.setFillAlpha(0.2)  # 20% opacity
    can.setFont("Helvetica", 60)
    can.setFillColorRGB(0.2, 0.2, 0.2)  # Dark gray

    # Get page dimensions
    width, height = letter

    # Draw watermark diagonally across the page
    can.saveState()
    can.translate(width / 2, height / 2)
    can.rotate(45)
    can.drawCentredString(0, 0, text)
    can.restoreState()

    can.save()
    packet.seek(0)
    return PdfReader(packet)


def add_watermark_to_pdf(
    input_file: Union[BinaryIO, BytesIO], output_stream: Optional[BytesIO] = None
) -> BytesIO:
    """Add watermark to a PDF file.

    Args:
        input_file: The input PDF file or stream.
        output_stream: Optional output stream to write to.

    Returns:
        BytesIO: A stream containing the watermarked PDF.
    """
    output_stream = output_stream or BytesIO()
    watermark = create_watermark()
    reader = PdfReader(input_file)
    writer = PdfWriter()

    total_pages = len(reader.pages)
    # Ensure we don't duplicate pages for very short PDFs
    watermark_pages = {
        min(i, total_pages - 1) for i in (0, total_pages // 2, total_pages - 1)
    }

    for page_num in range(total_pages):
        page = reader.pages[page_num]
        if page_num in watermark_pages:
            page.merge_page(watermark.pages[0])
        writer.add_page(page)

    writer.write(output_stream)
    output_stream.seek(0)
    return output_stream
