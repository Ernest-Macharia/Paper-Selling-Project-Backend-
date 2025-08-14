import logging

from django.db.models import Avg, Count
from rest_framework import serializers

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
    school_name = serializers.CharField(read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "name",
            "paper_count",
            "category",
            "average_price",
            "average_rating",
            "school_name",
        ]


class UserUploadSchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            "id",
            "name",
        ]


class SchoolSerializer(serializers.ModelSerializer):
    paper_count = serializers.SerializerMethodField()
    course_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_downloads = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "country",
            "website",
            "is_active",
            "paper_count",
            "course_count",
            "average_rating",
            "total_downloads",
            "slug",
        ]
        read_only_fields = ["slug"]

    def get_paper_count(self, obj):
        # Count of published papers for this school
        return obj.papers.filter(status="published").count()

    def get_course_count(self, obj):
        # Count of distinct courses with papers from this school
        return obj.papers.filter(status="published").values("course").distinct().count()

    def get_average_rating(self, obj):
        # Average rating of all papers from this school
        from django.db.models import Avg

        avg_rating = obj.papers.filter(status="published").aggregate(
            avg_rating=Avg("reviews__rating")
        )["avg_rating"]
        return round(avg_rating, 1) if avg_rating is not None else None

    def get_total_downloads(self, obj):
        # Sum of all downloads from papers in this school
        from django.db.models import Sum

        total = obj.papers.filter(status="published").aggregate(
            total_downloads=Sum("downloads")
        )["total_downloads"]
        return total if total is not None else 0


class PaperReviewSerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source="paper.title", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

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
    total_papers_sold = serializers.SerializerMethodField(read_only=True)
    reviews = PaperReviewSerializer(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    review_count = serializers.IntegerField(source="reviews.count", read_only=True)
    preview_url = serializers.SerializerMethodField()
    preview_image = serializers.SerializerMethodField()
    download_count = serializers.SerializerMethodField(read_only=True)
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
            "preview_image",
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
            "preview_image",
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
                if obj.file and hasattr(obj.file, "url"):
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
        if not request:
            return None

        try:
            if obj.preview_file and hasattr(obj.preview_file, "url"):
                url = obj.preview_file.url
                if not url.startswith(("http://", "https://")):
                    return request.build_absolute_uri(url)
                return url
            logger.warning(f"No preview file found for paper {obj.id}")
        except Exception as e:
            logger.error(f"Error generating preview URL for paper {obj.id}: {str(e)}")
        return None

    def get_preview_image(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        try:
            if obj.preview_image and hasattr(obj.preview_image, "url"):
                url = obj.preview_image.url
                if not url.startswith(("http://", "https://")):
                    return request.build_absolute_uri(url)
                return url
            logger.warning(f"No preview image found for paper {obj.id}")
        except Exception as e:
            logger.error(
                f"Error generating preview image URL for paper {obj.id}: {str(e)}"
            )
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
        request = self.context.get("request")
        user = obj.author
        avatar_url = (
            request.build_absolute_uri(user.avatar.url)
            if user.avatar and request
            else None
        )

        return {
            "id": user.id,
            "name": user.username,
            "email": user.email if request.user == user else None,
            "avatar": avatar_url,
            "papers_count": getattr(
                obj,
                "author_papers_count",
                user.papers.filter(status="published").count(),
            ),
            "papers_sold": getattr(
                obj,
                "author_papers_sold",
                user.papers.filter(status="published").exclude(is_free=True).count(),
            ),
        }

    def get_can_edit(self, obj):
        request = self.context.get("request")
        return request and request.user == obj.author

    def get_can_delete(self, obj):
        request = self.context.get("request")
        return request and request.user == obj.author

    def validate_file(self, file):
        max_size = 50 * 1024 * 1024  # 50MB
        if file.size > max_size:
            raise serializers.ValidationError("File size exceeds 50MB limit.")
        return file

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        paper = super().create(validated_data)

        if paper.file:
            paper.set_page_count()
            paper.generate_preview()
            paper.save(update_fields=["page_count", "preview_file", "preview_image"])

        return paper

    def update(self, instance, validated_data):
        file = validated_data.pop("file", None)
        instance = super().update(instance, validated_data)

        if file is not None:
            instance.file = file
            instance.set_page_count()
            instance.generate_preview()
            instance.save(
                update_fields=["file", "page_count", "preview_file", "preview_image"]
            )

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


class PaperListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    school = SchoolSerializer(read_only=True)

    download_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Paper
        fields = [
            "id",
            "title",
            "price",
            "upload_date",
            "category",
            "course",
            "school",
            "download_count",
            "average_rating",
            "review_count",
        ]


class SchoolDetailSerializer(serializers.ModelSerializer):
    papers = PaperSerializer(many=True, read_only=True)
    courses = serializers.SerializerMethodField()
    paper_count = serializers.IntegerField(read_only=True)
    course_count = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    total_downloads = serializers.IntegerField(read_only=True)

    class Meta:
        model = School
        fields = [
            "id",
            "name",
            "slug",
            "country",
            "website",
            "paper_count",
            "course_count",
            "average_rating",
            "total_downloads",
            "papers",
            "courses",
        ]

    def get_courses(self, obj):
        courses = (
            Course.objects.filter(papers__school=obj, papers__status="published")
            .annotate(paper_count=Count("papers"))
            .distinct()
        )
        return CourseSerializer(courses, many=True).data


class OrderSerializer(serializers.ModelSerializer):
    papers = PaperSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "papers", "price", "status", "created_at"]
