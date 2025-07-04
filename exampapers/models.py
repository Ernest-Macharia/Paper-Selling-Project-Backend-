import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now
from pypdf import PdfReader, PdfWriter

from backend import settings


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class School(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

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

    def generate_preview(self):
        if not self.file:
            return

        # Read original PDF
        self.file.seek(0)
        reader = PdfReader(self.file)
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
        self.preview_file.save(preview_name, ContentFile(buffer.read()), save=False)


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


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user}"


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
