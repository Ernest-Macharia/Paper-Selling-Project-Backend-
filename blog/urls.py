# blog/urls.py
from django.urls import path

from .views import (
    BlogPostDetailView,
    BlogPostListCreateView,
    CategoryListView,
    CommentCreateView,
    LikeToggleView,
    TagListView,
)

urlpatterns = [
    path("posts/", BlogPostListCreateView.as_view(), name="blog-list-create"),
    path("posts/<slug:slug>/", BlogPostDetailView.as_view(), name="blog-detail"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("tags/", TagListView.as_view(), name="tag-list"),
    path("<int:post_id>/comments/", CommentCreateView.as_view(), name="comment-create"),
    path("<int:post_id>/like/", LikeToggleView.as_view(), name="like-toggle"),
]
