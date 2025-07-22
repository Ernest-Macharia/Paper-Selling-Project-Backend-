import logging

from django.db.models import Avg
from rest_framework import serializers

from exampapers.utils.paper_helpers import generate_preview, set_page_count

from .models import Category, Course, Order, Paper, Review, School

logger = logging.getLogger(__name__)


class CategorySerializer(serializers.ModelSerializer):
    paper_count = serializers.IntegerField(read_only=True)
    average_price = serializers.FloatField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "paper_count", "average_price", "average_rating"]


class CourseSerializer(serializers.ModelSerializer):
    paper_count = serializers.IntegerField(read_only=True)
    average_price = serializers.FloatField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    category = serializers.CharField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "paper_count",
            "category",
            "average_price",
            "average_rating",
        ]


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ["id", "name"]


class PaperReviewSerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    user_name = serializers.CharField(source="user.first_name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "paper",
            "paper_title",
            "user_name",
            "user",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["paper", "user"]
        unique_together = ["user", "paper"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class PaperSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    school = SchoolSerializer(read_only=True)
    document_url = serializers.SerializerMethodField()
    author_info = serializers.SerializerMethodField()
    pages = serializers.SerializerMethodField()
    total_papers_sold = serializers.SerializerMethodField()
    reviews = PaperReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.IntegerField(source="reviews.count", read_only=True)
    preview_url = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    # Write-only fields for create/update
    category_id = serializers.PrimaryKeyRelatedField(
        source="category",
        queryset=Category.objects.all(),
        write_only=True,
        required=False,
    )
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Course.objects.all(), write_only=True, required=False
    )
    school_id = serializers.PrimaryKeyRelatedField(
        source="school", queryset=School.objects.all(), write_only=True, required=False
    )
    file = serializers.FileField(required=False, write_only=True, allow_null=True)

    class Meta:
        model = Paper
        fields = [
            "id",
            "title",
            "description",
            "file",
            "preview_file",
            "preview_url",
            "price",
            "status",
            "category",
            "course",
            "school",
            "category_id",
            "course_id",
            "school_id",
            "page_count",
            "views",
            "downloads",
            "download_count",
            "upload_date",
            "author",
            "author_info",
            "document_url",
            "pages",
            "total_papers_sold",
            "reviews",
            "average_rating",
            "review_count",
            "is_free",
            "can_edit",
            "can_delete",
            "year",
        ]
        read_only_fields = [
            "id",
            "author",
            "views",
            "downloads",
            "upload_date",
            "page_count",
            "document_url",
            "preview_url",
            "preview_file",
            "author_info",
        ]
        extra_kwargs = {"preview_file": {"read_only": True}}

    def get_document_url(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        try:
            user = request.user
            if obj.is_free:
                if obj.file and hasattr(obj.file, "url"):  # Add safety check
                    return request.build_absolute_uri(obj.file.url)
                return None

            if user.is_authenticated:
                has_bought = Order.objects.filter(
                    user=user, papers=obj, status="completed"
                ).exists()
                if (
                    (has_bought or obj.author == user)
                    and obj.file
                    and hasattr(obj.file, "url")
                ):
                    return request.build_absolute_uri(obj.file.url)
        except Exception as e:
            logger.error(f"Error generating document URL for paper {obj.id}: {str(e)}")
            return None
        return None

    def get_preview_url(self, obj):
        request = self.context.get("request")
        try:
            if hasattr(obj, "preview_file") and obj.preview_file and request:
                return request.build_absolute_uri(obj.preview_file.url)
        except Exception as e:
            logger.error(f"Error generating preview URL for paper {obj.id}: {str(e)}")
        return None

    def get_pages(self, obj):
        return obj.page_count

    def get_total_papers_sold(self, obj):
        return Order.objects.filter(papers=obj, status="completed").count()

    def get_download_count(self, obj):
        return obj.paperdownload_set.count()

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    def get_author_info(self, obj):
        user = obj.author
        request = self.context.get("request")
        avatar_url = (
            request.build_absolute_uri(user.avatar.url)
            if user.avatar and request
            else None
        )

        return {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "email": user.email if user == request.user else None,
            "avatar": avatar_url,
            "papers_sold": user.papers.filter(status="published")
            .exclude(is_free=True)
            .count(),
        }

    def get_can_edit(self, obj):
        request = self.context.get("request")
        return request and request.user == obj.author

    def get_can_delete(self, obj):
        request = self.context.get("request")
        return request and request.user == obj.author

    def create(self, validated_data):
        # Set the author to the current user
        validated_data["author"] = self.context["request"].user
        paper = super().create(validated_data)

        # Process file if provided
        if paper.file:
            set_page_count(paper)
            generate_preview(paper)
            paper.save()

        return paper

    def update(self, instance, validated_data):
        # Handle file upload separately if present
        file = validated_data.pop("file", None)

        # Update other fields
        instance = super().update(instance, validated_data)

        # Update file if provided
        if file is not None:  # Explicit None check to handle file removal
            if file:  # New file provided
                # Delete old files
                if instance.file:
                    instance.file.delete()
                if instance.preview_file:
                    instance.preview_file.delete()

                instance.file = file
                set_page_count(instance)
                generate_preview(instance)
            else:  # File removal requested
                if instance.file:
                    instance.file.delete()
                    instance.file = None
                if instance.preview_file:
                    instance.preview_file.delete()
                    instance.preview_file = None
                instance.page_count = 0

            instance.save()

        return instance

    def validate(self, data):
        """
        Add custom validation for paper updates
        """
        request = self.context.get("request")
        instance = self.instance

        # For updates, verify the user owns the paper
        if instance and request and instance.author != request.user:
            raise serializers.ValidationError("You can only modify your own papers.")

        # Validate price for non-free papers
        if not data.get("is_free", False if instance is None else instance.is_free):
            if "price" in data and data["price"] <= 0:
                raise serializers.ValidationError(
                    "Price must be greater than 0 for non-free papers."
                )

        return data


class OrderSerializer(serializers.ModelSerializer):
    papers = PaperSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "papers", "price", "status", "created_at"]
