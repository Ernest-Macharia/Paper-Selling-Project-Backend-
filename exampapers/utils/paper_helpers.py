import logging
import os
import tempfile
from io import BytesIO
from typing import BinaryIO, Optional, Union

from django.core.files.base import ContentFile
from pdf2image import convert_from_bytes
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
    """Generate a responsive preview PDF optimized for all devices.

    Rules:
    - No preview for papers with less than 6 pages
    - 1 page preview for papers with 6-9 pages
    - 2 page preview for papers with 10-49 pages
    - 3 page preview for papers with 50+ pages

    Additional improvements:
    - Converts to A4 size for consistency
    - Adds mobile-friendly margins
    - Generates fallback images for devices that can't preview PDFs
    """
    if not self.file:
        return

    try:
        with self.file.open("rb") as f:
            reader = PdfReader(f)
            total_pages = len(reader.pages)

            # Determine how many pages to include in preview
            if total_pages < 6:
                return  # No preview for very short papers
            elif total_pages < 10:
                preview_pages = 1
            elif total_pages < 50:
                preview_pages = 2
            else:
                preview_pages = 3

            writer = PdfWriter()

            # Add the determined number of pages with mobile optimization
            for page in reader.pages[:preview_pages]:
                # Create a new page with proper dimensions and margins
                new_page = writer.add_blank_page(
                    width=595,  # A4 width in points (210mm)
                    height=842,  # A4 height in points (297mm)
                )

                # Scale and center the original page with margins
                original_width = float(page.mediabox[2])
                original_height = float(page.mediabox[3])

                # Calculate scaling factor to fit within A4 with margins
                margin = 20  # points
                max_width = 595 - (2 * margin)
                max_height = 842 - (2 * margin)

                width_ratio = max_width / original_width
                height_ratio = max_height / original_height
                scale = min(width_ratio, height_ratio)

                # Center the scaled page
                x_offset = (595 - (original_width * scale)) / 2
                y_offset = (842 - (original_height * scale)) / 2

                # Merge the scaled page
                page.scale(scale, scale)
                new_page.merge_page(page)
                new_page.merge_transformed_page(
                    page, (scale, 0, 0, scale, x_offset, y_offset), expand=True
                )

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

            # Generate fallback image for mobile devices
            self._generate_preview_image(buffer)

            self.save(update_fields=["preview_file", "preview_image"])
    except Exception as e:
        logger.error(f"Error generating preview for paper {self.id}: {str(e)}")


def _generate_preview_image(self, pdf_buffer: BytesIO) -> None:
    """Generate a fallback image preview for mobile devices."""
    try:

        # Convert first page to image
        images = convert_from_bytes(
            pdf_buffer.getvalue(), dpi=100, first_page=1, last_page=1, fmt="jpeg"
        )

        if images:
            with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_img:
                images[0].save(temp_img, format="JPEG", quality=85)
                temp_img.seek(0)

                preview_image_name = (
                    os.path.splitext(os.path.basename(self.file.name))[0]
                    + "_preview.jpg"
                )
                self.preview_image.save(
                    preview_image_name, ContentFile(temp_img.read()), save=False
                )
    except Exception as e:
        logger.warning(f"Couldn't generate image preview: {str(e)}")


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
