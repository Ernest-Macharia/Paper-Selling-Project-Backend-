from django.db.models import Avg
from rest_framework import serializers

from .models import Category, Course, Order, Paper, Review, School


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

    class Meta:
        model = Course
        fields = ["id", "name", "paper_count", "average_price", "average_rating"]


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

    # Write-only fields to accept IDs when creating/updating
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True
    )
    course_id = serializers.PrimaryKeyRelatedField(
        source="course", queryset=Course.objects.all(), write_only=True
    )
    school_id = serializers.PrimaryKeyRelatedField(
        source="school", queryset=School.objects.all(), write_only=True
    )
    download_count = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = "__all__"
        read_only_fields = ["author"]

    def get_document_url(self, obj):
        request = self.context.get("request")
        user = request.user

        if obj.is_free:
            return request.build_absolute_uri(obj.file.url)

        if user.is_authenticated:
            has_bought = Order.objects.filter(
                user=user, papers=obj, status="completed"
            ).exists()
            if has_bought:
                return request.build_absolute_uri(obj.file.url)

        # fallback to preview
        return None

    def get_preview_url(self, obj):
        request = self.context.get("request")
        if obj.preview_file and request:
            return request.build_absolute_uri(obj.preview_file.url)
        return None

    def get_pages(self, obj):
        # Assuming a helper method exists to count PDF pages
        return obj.page_count if hasattr(obj, "page_count") else None

    def get_total_papers_sold(self, obj):
        return Order.objects.filter(papers=obj).count()

    def get_download_count(self, obj):
        return obj.paperdownload_set.count()

    def get_average_rating(self, obj):
        return obj.reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    def get_author_info(self, obj):
        user = obj.author
        return {
            "name": f"{user.first_name} {user.last_name}".strip(),
            "email": user.email,
            "avatar": (
                self.context["request"].build_absolute_uri(user.avatar.url)
                if user.avatar
                else None
            ),
            "papers_sold": user.papers.filter(status="published")
            .exclude(is_free=True)
            .count(),
        }


class OrderSerializer(serializers.ModelSerializer):
    papers = PaperSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "papers", "price", "status", "created_at"]
