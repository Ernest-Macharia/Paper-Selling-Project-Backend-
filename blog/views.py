from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BlogPost, Category, Like, Tag
from .serializers import (
    BlogPostSerializer,
    CategorySerializer,
    CommentSerializer,
    TagSerializer,
)


# Custom permission to allow only admin users to create/update/delete
class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # SAFE_METHODS = GET, HEAD, OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
        # Only admin/staff can POST, PUT, PATCH, DELETE
        return request.user and request.user.is_staff


# Blog posts: Anyone can read, only admin can create/edit/delete
class BlogPostListCreateView(generics.ListCreateAPIView):
    queryset = BlogPost.objects.filter(is_published=True)
    serializer_class = BlogPostSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        # Everyone only sees published posts
        return BlogPost.objects.filter(is_published=True)

    def perform_create(self, serializer):
        # Automatically assign the logged-in admin as author
        serializer.save(author=self.request.user)


# Blog post details: anyone can view, only admin can edit/delete
class BlogPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"


# Categories and tags — only admin can create, everyone can view
class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class TagListView(generics.ListCreateAPIView):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAdminOrReadOnly]


# Comments — anyone can post a comment
class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        post_id = self.kwargs.get("post_id")
        try:
            post = BlogPost.objects.get(id=post_id)
        except BlogPost.DoesNotExist:
            raise NotFound("Blog post not found.")

        # If not logged in, leave user null (if your model allows)
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user, post=post)


# Likes — anyone can like/unlike (optional: require login)
class LikeToggleView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, post_id):
        post = BlogPost.objects.get(id=post_id)

        # Prevent anonymous likes if your model requires user
        if not request.user.is_authenticated:
            return Response(
                {"error": "Login required to like posts."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({"message": "Unliked"}, status=status.HTTP_200_OK)
        return Response({"message": "Liked"}, status=status.HTTP_201_CREATED)
