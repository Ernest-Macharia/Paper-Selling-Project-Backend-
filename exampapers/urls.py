from django.urls import path

from .views import (
    AllPapersView,
    CategoryListView,
    CourseListView,
    CreateOrderView,
    DashboardStatsView,
    GivenReviewsListAPIView,
    LatestPapersView,
    LatestUserPapersView,
    MostViewedPapersView,
    OrderDetailView,
    PaperDeleteView,
    PaperDetailView,
    PaperDownloadView,
    PaperReviewCreateAPIView,
    PapersByAuthorView,
    PaperUpdateView,
    PaperUploadView,
    PopularCategoriesView,
    PopularCoursesView,
    PopularSchoolsView,
    ReceivedReviewsListAPIView,
    SchoolCoursesView,
    SchoolDetailView,
    SchoolListView,
    SchoolPapersView,
    UploaadCourseListView,
    UserDownloadsView,
    UserOrderListView,
    UserUploadSchoolListView,
    UserUploadsView,
)

urlpatterns = [
    path("upload/", PaperUploadView.as_view(), name="upload"),
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("courses/", CourseListView.as_view(), name="course-list"),
    path("popular-courses/", PopularCoursesView.as_view(), name="popular-courses"),
    path("upload-courses/", UploaadCourseListView.as_view(), name="upload-courses"),
    path(
        "popular-categories/",
        PopularCategoriesView.as_view(),
        name="popular-categories",
    ),
    path("popular-schools/", PopularSchoolsView.as_view(), name="popular-schools"),
    path(
        "user-upload-schools/", UserUploadSchoolListView.as_view(), name="school-list"
    ),
    path("orders/", UserOrderListView.as_view(), name="user-orders"),
    path("create-order/", CreateOrderView.as_view(), name="order-create"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("papers/", AllPapersView.as_view(), name="all-papers"),
    path("papers/<int:pk>/", PaperDetailView.as_view(), name="paper-detail"),
    path(
        "papers/author/<int:author_id>/",
        PapersByAuthorView.as_view(),
        name="papers-by-author",
    ),
    path(
        "papers/<int:pk>/download/", PaperDownloadView.as_view(), name="paper-download"
    ),
    path("papers/most-viewed/", MostViewedPapersView.as_view(), name="most-viewed"),
    path("papers/latest-papers/", LatestPapersView.as_view(), name="latest-papers"),
    path("dashboard/latest-papers/", LatestUserPapersView.as_view()),
    path("my-uploads/", UserUploadsView.as_view(), name="user-uploads"),
    path("my-downloads/", UserDownloadsView.as_view(), name="user-downloads"),
    path("papers/update/<int:pk>/", PaperUpdateView.as_view(), name="paper-update"),
    path("papers/<int:pk>/delete/", PaperDeleteView.as_view(), name="paper-delete"),
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("schools/", SchoolListView.as_view(), name="school-list"),
    path("schools/<int:pk>/", SchoolDetailView.as_view(), name="school-detail"),
    path("schools/<int:pk>/papers/", SchoolPapersView.as_view(), name="school-papers"),
    path(
        "schools/<int:pk>/courses/", SchoolCoursesView.as_view(), name="school-courses"
    ),
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
