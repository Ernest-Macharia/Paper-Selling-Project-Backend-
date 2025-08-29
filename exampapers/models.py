import logging
import os
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
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
    file = models.FileField(upload_to="papers/")
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
        School, on_delete=models.SET_NULL, null=True, blank=True, related_name="papers"
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

    def __str__(self):
        return self.title

    def increment_downloads(self):
        """Increase download count"""
        self.downloads += 1
        self.save(update_fields=["downloads"])

    def increment_views(self):
        """Increase view count"""
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
            raise RuntimeError(f"Failed to set page count: {e}")

    def generate_preview(self) -> None:
        """Generate preview PDF and image for this Paper."""

        if self.preview_file and self.preview_file.storage.exists(
            self.preview_file.name
        ):
            logger.info(f"Preview already exists for paper {self.id}, skipping.")
            return
        if not self.file:
            return
        if not self.file:
            logger.warning(
                f"No file found for paper {self.id}, skipping preview generation"
            )
            return

        try:
            # Ensure the file exists in storage
            if not self.file.storage.exists(self.file.name):
                logger.error(f"File {self.file.name} doesn't exist in storage")
                return

            with self.file.open("rb") as f:
                try:
                    reader = PdfReader(f)
                    total_pages = len(reader.pages)
                except Exception as e:
                    logger.error(f"Invalid PDF file for paper {self.id}: {str(e)}")
                    return

                if total_pages < 1:
                    logger.info(f"Paper {self.id} has no pages, skipping preview")
                    return

                # Determine how many preview pages to generate
                if total_pages > 21:
                    preview_pages = min(4, total_pages)
                elif total_pages < 20:
                    preview_pages = min(2, total_pages)
                else:
                    preview_pages = 0

                if preview_pages == 0:
                    logger.info(
                        f"Paper {self.id} has less than 5 pages, skipping PDF preview generation"
                    )
                    f.seek(0)
                    self._generate_preview_image(BytesIO(f.read()))
                    return

                writer = PdfWriter()

                for i in range(preview_pages):
                    page = reader.pages[i]
                    orig_width = float(page.mediabox.width)
                    orig_height = float(page.mediabox.height)
                    scale = min((595 - 40) / orig_width, (842 - 40) / orig_height)

                    writer.add_blank_page(width=595, height=842)
                    new_page = writer.pages[-1]

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

                pdf_buffer = BytesIO()
                writer.write(pdf_buffer)
                pdf_buffer.seek(0)

                preview_name = f"previews/{self.id}_{os.path.basename(self.file.name)}"
                self.preview_file.save(
                    preview_name, ContentFile(pdf_buffer.getvalue()), save=False
                )

                # Generate image from the first page
                self._generate_preview_image(pdf_buffer)

        except Exception as e:
            logger.error(
                f"Failed to generate preview for paper {self.id}: {str(e)}",
                exc_info=True,
            )
            raise

    def _generate_preview_image(self, pdf_buffer: BytesIO):
        if self.preview_image and self.preview_image.storage.exists(
            self.preview_image.name
        ):
            logger.info(f"Preview image already exists for paper {self.id}, skipping.")
            return
        try:
            images = convert_from_bytes(
                pdf_buffer.getvalue(), dpi=300, first_page=1, last_page=1, fmt="jpeg"
            )
            if images:
                img_buffer = BytesIO()
                images[0].save(img_buffer, format="JPEG", quality=95)
                img_buffer.seek(0)
                preview_image_name = f"{os.path.splitext(os.path.basename(self.file.name))[0]}_preview.jpg"
                self.preview_image.save(
                    preview_image_name, ContentFile(img_buffer.getvalue()), save=False
                )
        except Exception as e:
            logger.warning(f"Couldn't generate image preview for {self.id}: {e}")

    def save(self, *args, **kwargs):
        if self.file:
            try:
                original_file = Paper.objects.get(pk=self.pk).file if self.pk else None
            except Paper.DoesNotExist:
                original_file = None

            if not original_file or original_file.name != self.file.name:
                watermarked_buffer = add_watermark_to_pdf(self.file.open("rb"))
                original_name = os.path.basename(self.file.name)
                if not original_name.startswith("watermarked_"):
                    original_name = f"watermarked_{original_name}"
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
