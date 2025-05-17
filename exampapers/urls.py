from django.urls import path
from .views import (
    PaperUploadView,
    AllPapersView,
    PaperDetailView,
    UserUploadsView,
    UserDownloadsView,
    CategoryListView,
    CourseListView,
    PopularCoursesView,
    SchoolListView
)

urlpatterns = [
    path('upload/', PaperUploadView.as_view(), name="upload"),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('popular-courses/', PopularCoursesView.as_view(), name='popular-courses'),
    path('schools/', SchoolListView.as_view(), name='school-list'),

    path('papers/', AllPapersView.as_view(), name='all-papers'),
    path('papers/<int:pk>/', PaperDetailView.as_view(), name='paper-detail'),
    path('my-uploads/', UserUploadsView.as_view(), name='user-uploads'),
    path('my-downloads/', UserDownloadsView.as_view(), name='user-downloads'),
]
