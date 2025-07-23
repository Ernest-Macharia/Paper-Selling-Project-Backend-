import logging
import os
import re
import time
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
from django.utils.timezone import now
from pdf2image import convert_from_bytes
from pypdf import PdfReader, PdfWriter

from exampapers.utils.paper_helpers import add_watermark_to_pdf

logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class School(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.country})"


class Course(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    schools = models.ManyToManyField(School, related_name="courses")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Paper(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="papers"
    )
    description = models.TextField(blank=True)
    file = models.FileField(
        upload_to="papers/", validators=[MaxValueValidator(50 * 1024 * 1024)]
    )
    preview_file = models.FileField(upload_to="previews/", blank=True, null=True)
    preview_image = models.ImageField(
        upload_to="preview_images/", blank=True, null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="papers",
    )
    course = models.ForeignKey(
        Course, on_delete=models.SET_NULL, null=True, blank=True, related_name="papers"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="papers",
    )
    upload_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloads = models.PositiveIntegerField(default=0)
    uploads = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Set price for premium papers",
    )
    is_free = models.BooleanField(
        default=False, help_text="Check this if the paper is free"
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="published"
    )
    page_count = models.IntegerField(null=True, blank=True)
    year = models.CharField(
        max_length=9,
        blank=True,
        null=True,
        help_text="Academic year format: YYYY/YYYY (e.g., 2023/2024)",
    )

    class Meta:
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["upload_date"]),
            models.Index(fields=["author"]),
        ]
        ordering = ["-upload_date"]

    def __str__(self):
        return self.title

    def clean(self):
        """Validate model before saving."""
        super().clean()

        # Validate file extension
        if self.file:
            ext = os.path.splitext(self.file.name)[1].lower()
            if ext != ".pdf":
                raise ValidationError("Only PDF files are allowed.")

        # Validate year format
        if self.year and not re.match(r"^\d{4}/\d{4}$", self.year):
            raise ValidationError("Year must be in format YYYY/YYYY")

    def increment_downloads(self):
        """Increase download count."""
        self.downloads += 1
        self.save(update_fields=["downloads"])

    def increment_views(self):
        """Increase view count."""
        self.views += 1
        self.save(update_fields=["views"])

    def set_page_count(self) -> None:
        """Set the number of pages for this Paper."""
        if not self.file:
            return

        try:
            with self.file.open("rb") as f:
                reader = PdfReader(f)
                self.page_count = len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to set page count for paper {self.id}: {str(e)}")
            self.page_count = None

    def generate_preview(self) -> None:
        """Generate preview PDF and image for this Paper."""
        if not self.file:
            logger.warning(f"No file found for paper {self.id}")
            return

        try:
            if not self.file.storage.exists(self.file.name):
                logger.error(f"File {self.file.name} doesn't exist in storage")
                return

            with self.file.open("rb") as f:
                try:
                    reader = PdfReader(f)
                    total_pages = len(reader.pages)

                    if total_pages < 1:
                        logger.info(f"Paper {self.id} has no pages")
                        return

                    # Determine which pages to include in preview
                    if total_pages < 5:
                        # Skip PDF preview for very short documents
                        logger.info(
                            f"Paper {self.id} has less than 5 pages, skipping PDF preview"
                        )
                        f.seek(0)
                        self._generate_preview_image(BytesIO(f.read()))
                        return
                    elif total_pages < 20:
                        # For medium documents, show first 2 pages
                        preview_pages = list(range(min(2, total_pages)))
                    else:
                        # For large documents, show first 4 pages
                        preview_pages = list(range(min(4, total_pages)))

                    writer = PdfWriter()

                    for page_num in preview_pages:
                        page = reader.pages[page_num]
                        orig_width = float(page.mediabox.width)
                        orig_height = float(page.mediabox.height)

                        # Calculate scale to fit on A4 (595x842 points)
                        scale = min((595 - 40) / orig_width, (842 - 40) / orig_height)

                        # Add blank page and center the content
                        writer.add_blank_page(width=595, height=842)
                        new_page = writer.pages[-1]

                        new_page.merge_transformed_page(
                            page,
                            (
                                scale,
                                0,
                                0,
                                scale,
                                (595 - orig_width * scale) / 2,  # Center horizontally
                                (842 - orig_height * scale) / 2,  # Center vertically
                            ),
                        )

                    pdf_buffer = BytesIO()
                    writer.write(pdf_buffer)
                    pdf_buffer.seek(0)

                    # Save preview PDF with timestamp
                    ts = int(time.time())
                    preview_name = f"previews/{self.id}_preview_{ts}.pdf"
                    self.preview_file.save(
                        preview_name, ContentFile(pdf_buffer.getvalue()), save=False
                    )

                    # Generate preview image from the first page
                    self._generate_preview_image(pdf_buffer)

                except Exception as e:
                    logger.error(f"Invalid PDF for paper {self.id}: {str(e)}")
                    return

        except Exception as e:
            logger.error(
                f"Failed to generate preview for paper {self.id}: {str(e)}",
                exc_info=True,
            )
            raise

    def _generate_preview_image(self, pdf_buffer: BytesIO) -> None:
        """Generate optimized preview image for mobile devices."""
        try:
            images = convert_from_bytes(
                pdf_buffer.getvalue(),
                dpi=200,
                first_page=1,
                last_page=1,
                size=(1200, None),  # Width 1200px, maintain aspect ratio
                fmt="jpeg",
                thread_count=2,
            )

            if images:
                img_buffer = BytesIO()
                img = images[0].convert("RGB")

                img.save(
                    img_buffer,
                    format="JPEG",
                    quality=85,
                    optimize=True,
                    progressive=True,
                )

                ts = int(time.time())
                preview_image_name = f"previews/{self.id}_preview_{ts}.jpg"

                self.preview_image.save(
                    preview_image_name, ContentFile(img_buffer.getvalue()), save=False
                )
        except Exception as e:
            logger.error(
                f"Image preview generation failed for paper {self.id}: {str(e)}"
            )
            self._generate_placeholder_preview()

    def _generate_placeholder_preview(self):
        """Generate a simple placeholder image."""
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (800, 1131), color=(240, 240, 240))
        d = ImageDraw.Draw(img)
        d.text((100, 100), "Preview Unavailable", fill=(100, 100, 100))

        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)

        self.preview_image.save(
            f"previews/{self.id}_placeholder.jpg",
            ContentFile(buffer.getvalue()),
            save=False,
        )

    def delete(self, *args, **kwargs):
        """Clean up files when paper is deleted."""
        storage = self.file.storage
        if storage.exists(self.file.name):
            storage.delete(self.file.name)
        if self.preview_file and storage.exists(self.preview_file.name):
            storage.delete(self.preview_file.name)
        if self.preview_image and storage.exists(self.preview_image.name):
            storage.delete(self.preview_image.name)
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Override save to handle watermarking and preview generation."""
        self.clean()  # Run validation before saving

        # Process watermarking if file changed
        if self.file:
            try:
                original = Paper.objects.get(pk=self.pk) if self.pk else None
            except Paper.DoesNotExist:
                original = None

            if not original or original.file.name != self.file.name:
                watermarked_buffer = add_watermark_to_pdf(self.file.open("rb"))
                original_name = f"watermarked_{os.path.basename(self.file.name)}"
                self.file.save(
                    original_name,
                    ContentFile(watermarked_buffer.getvalue()),
                    save=False,
                )

        super().save(*args, **kwargs)


@receiver(post_save, sender=Paper)
def handle_paper_save(sender, instance, created, **kwargs):
    """Automatically generate previews and set page count."""
    try:
        if created or not instance.preview_file:
            instance.set_page_count()
            instance.generate_preview()
            instance.save()
    except Exception as e:
        logger.error(f"Failed to process paper {instance.id}: {str(e)}")


class Review(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.rating}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    papers = models.ManyToManyField(Paper)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    credited = models.BooleanField(default=False)

    def __str__(self):
        return f"Order {self.id} - {self.user}"


class PaperDownload(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    paper = models.ForeignKey("Paper", on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} downloaded {self.paper.title} on {self.downloaded_at}"


class Wishlist(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist"
    )
    paper = models.ForeignKey(
        Paper, on_delete=models.CASCADE, related_name="wishlisted_by"
    )
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.paper.title}"


class Statistics(models.Model):
    """Model to track platform-wide statistics"""

    date = models.DateField(default=now, unique=True)
    total_papers = models.PositiveIntegerField(default=0)
    total_downloads = models.PositiveIntegerField(default=0)
    total_uploads = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_users = models.PositiveIntegerField(default=0)
    new_users_today = models.PositiveIntegerField(default=0)
    papers_uploaded_today = models.PositiveIntegerField(default=0)
    total_orders = models.PositiveIntegerField(default=0)
    completed_orders = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Statistics"

    def __str__(self):
        return f"Stats for {self.date}"
