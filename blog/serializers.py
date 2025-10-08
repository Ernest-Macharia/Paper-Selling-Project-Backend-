# blog/serializers.py
from rest_framework import serializers

from .models import BlogPost, Category, Comment, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Comment
        fields = ["id", "user", "user_name", "content", "created_at"]
        read_only_fields = ["user", "created_at"]


class BlogPostSerializer(serializers.ModelSerializer):
    author_name = serializers.ReadOnlyField(source="author.username")
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), write_only=True, source="category"
    )
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), write_only=True, source="tags"
    )
    comments = CommentSerializer(many=True, read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "author",
            "author_name",
            "title",
            "slug",
            "content",
            "image",
            "category",
            "category_id",
            "tags",
            "tag_ids",
            "is_published",
            "likes_count",
            "comments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["slug", "author", "created_at", "updated_at"]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        post = BlogPost.objects.create(**validated_data)
        post.tags.set(tags)
        return post

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance
