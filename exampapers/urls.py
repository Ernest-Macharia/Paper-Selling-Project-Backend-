from django.urls import path

from .views import (
    AllPapersView,
    CategoryListView,
    CourseListView,
    CreateOrderView,
    DashboardStatsView,
    GivenReviewsListAPIView,
    LatestUserPapersView,
    MostViewedPapersView,
    OrderDetailView,
    PaperDetailView,
    PaperDownloadView,
    PaperReviewCreateAPIView,
    PaperUploadView,
    PopularCategoriesView,
    PopularCoursesView,
    ReceivedReviewsListAPIView,
    SchoolListView,
    UserDownloadsView,
    UserOrderListView,
    UserUploadsView,
)

urlpatterns = [
    path("upload/", PaperUploadView.as_view(), name="upload"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("popular-courses/", PopularCoursesView.as_view(), name="popular-courses"),
    path(
        "popular-categories/",
        PopularCategoriesView.as_view(),
        name="popular-categories",
    ),
    path("schools/", SchoolListView.as_view(), name="school-list"),
    path("orders/", UserOrderListView.as_view(), name="user-orders"),
    path("create-order/", CreateOrderView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("papers/", AllPapersView.as_view(), name="all-papers"),
    path("papers/<int:pk>/", PaperDetailView.as_view(), name="paper-detail"),
    path(
        "papers/<int:pk>/download/", PaperDownloadView.as_view(), name="paper-download"
    ),
    path("papers/most-viewed/", MostViewedPapersView.as_view(), name="most-viewed"),
    path("dashboard/latest-papers/", LatestUserPapersView.as_view()),
    path("my-uploads/", UserUploadsView.as_view(), name="user-uploads"),
    path("my-downloads/", UserDownloadsView.as_view(), name="user-downloads"),
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path(
        "papers/<int:pk>/download/reviews/",
        PaperReviewCreateAPIView.as_view(),
        name="paper-review-create",
    ),
    path("reviews/given/", GivenReviewsListAPIView.as_view(), name="reviews-given"),
    path(
        "reviews/received/",
        ReceivedReviewsListAPIView.as_view(),
        name="reviews-received",
    ),
]
