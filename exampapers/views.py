import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exampapers.utils.paper_helpers import generate_preview, set_page_count
from payments.models import Wallet
from users.models import User

from .models import (
    Category,
    Course,
    Order,
    Paper,
    PaperDownload,
    Review,
    School,
    Wishlist,
)
from .serializers import (
    CategorySerializer,
    CourseSerializer,
    OrderSerializer,
    PaperReviewSerializer,
    PaperSerializer,
    SchoolSerializer,
)

logger = logging.getLogger(__name__)


class PaperFilterMixin:
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["category", "course", "school", "status", "is_free"]
    search_fields = [
        "title",
        "description",
        "author__username",
        "category__name",
        "course__name",
        "school__name",
    ]
    ordering_fields = [
        "title",
        "upload_date",
        "downloads",
        "views",
        "price",
        "earnings",
        "category__name",
        "course__name",
        "school__name",
    ]
    ordering = ["-upload_date"]


class AllPapersView(PaperFilterMixin, generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Only published papers, can add filtering and searching from mixin
        return Paper.objects.filter(status="published").select_related(
            "category", "course", "school"
        )


class UserUploadsView(generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["title", "description"]
    ordering_fields = ["upload_date", "title", "views", "downloads"]
    ordering = ["-upload_date"]

    def get_queryset(self):
        return Paper.objects.filter(author=self.request.user).select_related(
            "category", "course", "school"
        )


class UserDownloadsView(ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Paper.objects.filter(paperdownload__user=self.request.user)
            .distinct()
            .select_related("category", "course", "school")
        )

    def list(self, request, *args, **kwargs):
        papers = self.get_queryset()
        serialized = self.get_serializer(
            papers, many=True, context={"request": request}
        )

        # Get download timestamps from PaperDownload model
        download_map = {
            d.paper_id: d.downloaded_at
            for d in PaperDownload.objects.filter(user=request.user, paper__in=papers)
        }

        enriched_data = []
        for paper_data in serialized.data:
            paper_id = paper_data["id"]
            enriched_data.append(
                {
                    **paper_data,
                    "download_date": download_map.get(paper_id),
                    "file": paper_data.get("document_url"),
                }
            )

        return Response(enriched_data)


class PaperDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        paper = get_object_or_404(Paper, pk=pk, status="published")
        Paper.objects.filter(pk=paper.pk).update(views=F("views") + 1)
        serializer = PaperSerializer(paper, context={"request": request})
        return Response(serializer.data)


class MostViewedPapersView(ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(status="published").order_by("-views")


class LatestUserPapersView(ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(author=self.request.user).order_by("-upload_date")


class PaperUploadView(generics.CreateAPIView):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        # Save the paper first
        paper = serializer.save(author=self.request.user)

        # Then process page count and preview if file is present
        if paper.file:
            set_page_count(paper)
            generate_preview(paper)


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Category.objects.annotate(
            paper_count=Count("papers", filter=Q(papers__status="published")),
            average_price=Avg("papers__price", filter=Q(papers__status="published")),
            average_rating=Avg("papers__reviews__rating"),
        ).order_by("-paper_count")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name"]
    ordering_fields = ["name", "paper_count", "average_price", "average_rating"]
    ordering = ["-paper_count"]


class CourseListView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Course.objects.annotate(
            paper_count=Count("papers", filter=Q(papers__status="published")),
            average_price=Avg("papers__price", filter=Q(papers__status="published")),
            average_rating=Avg("papers__reviews__rating"),
        ).order_by("-paper_count")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name"]
    ordering_fields = ["name", "paper_count", "average_price", "average_rating"]
    ordering = ["-paper_count"]


class PopularCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Popular by number of published papers only
        return Course.objects.annotate(
            paper_count=Count("papers", filter=Q(papers__status="published"))
        ).order_by("-paper_count")[:10]


class PopularCategoriesView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Popular by number of published papers only
        return Category.objects.annotate(
            paper_count=Count("papers", filter=Q(papers__status="published"))
        ).order_by("-paper_count")[:10]


class SchoolListView(generics.ListAPIView):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by("-created_at")


# Retrieve a single order by id (optional)
class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class CreateOrderView(generics.CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]


class DashboardStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = now().date()

        # 🌐 Global Statistics
        papers_qs = Paper.objects.filter(status="published")
        total_users = User.objects.count()
        total_papers = papers_qs.count()
        total_downloads = papers_qs.aggregate(total=Sum("downloads"))["total"] or 0
        total_uploads = papers_qs.aggregate(total=Sum("uploads"))["total"] or 0
        total_views = papers_qs.aggregate(total=Sum("views"))["total"] or 0
        total_earnings = papers_qs.aggregate(total=Sum("earnings"))["total"] or 0
        total_orders = Order.objects.count()
        completed_orders = Order.objects.filter(status="completed").count()
        new_users_today = User.objects.filter(date_joined__date=today).count()
        papers_uploaded_today = Paper.objects.filter(upload_date__date=today).count()

        # 👤 User-specific Stats
        user_papers = Paper.objects.filter(author=user)
        user_downloaded_papers = PaperDownload.objects.filter(user=user).count()
        user_views = user_papers.aggregate(total=Sum("views"))["total"] or 0
        user_earnings = user_papers.aggregate(total=Sum("earnings"))["total"] or 0
        user_orders = Order.objects.filter(user=user)
        user_reviews = Review.objects.filter(user=user).count()
        user_wishlist_count = Wishlist.objects.filter(user=user).count()

        # ✅ Wallet Earnings
        wallet, _ = Wallet.objects.get_or_create(user=user)

        return Response(
            {
                # 🌐 Platform-wide
                "total_users": total_users,
                "new_users_today": new_users_today,
                "total_papers": total_papers,
                "papers_uploaded_today": papers_uploaded_today,
                "total_downloads": total_downloads,
                "total_uploads": total_uploads,
                "total_views": total_views,
                "total_orders": total_orders,
                "completed_orders": completed_orders,
                "total_earnings": float(total_earnings),
                # 👤 User-specific
                "user_name": user.get_full_name() or user.username,
                "user_papers_uploaded": user_papers.count(),
                "user_total_downloads": user_downloaded_papers,
                "user_total_views": user_views,
                "user_total_earnings_from_papers": float(user_earnings),
                "user_orders": user_orders.count(),
                "user_completed_orders": user_orders.filter(status="completed").count(),
                "user_review_count": user_reviews,
                "user_wishlist_count": user_wishlist_count,
                # 💰 Wallet Earnings
                "wallet_total_earned": float(wallet.total_earned),
                "wallet_total_withdrawn": float(wallet.total_withdrawn),
                "wallet_available_balance": float(wallet.available_balance),
            }
        )


class PaperDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            paper = Paper.objects.get(pk=pk)
        except Paper.DoesNotExist:
            return Response({"detail": "Paper not found."}, status=404)

        # Check if user owns the paper
        if not Order.objects.filter(
            user=request.user, papers=paper, status="completed"
        ).exists():
            return Response(
                {"detail": "You have not purchased this paper."}, status=403
            )

        PaperDownload.objects.create(
            user=request.user, paper=paper, ip_address=self.get_client_ip(request)
        )

        # Send email notification
        self.send_download_email(request.user, paper)

        return Response({"file_url": request.build_absolute_uri(paper.file.url)})

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")

    def send_download_email(self, user, paper):
        subject = f"You downloaded: {paper.title}"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = user.email

        html_content = render_to_string(
            "emails/paper_download_email.html",
            {
                "user": user,
                "paper": paper,
                "download_time": datetime.now().strftime("%B %d, %Y at %I:%M %p"),
                "year": datetime.now().year,
            },
        )
        text_content = f"You downloaded the paper: {paper.title}"

        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()


class PaperReviewCreateAPIView(generics.CreateAPIView):
    queryset = Review.objects.all()
    serializer_class = PaperReviewSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        paper_id = self.kwargs.get("pk")
        paper = get_object_or_404(Paper, pk=paper_id)
        serializer.save(user=self.request.user, paper=paper)


class GivenReviewsListAPIView(generics.ListAPIView):
    serializer_class = PaperReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(user=self.request.user).order_by("-created_at")


class ReceivedReviewsListAPIView(generics.ListAPIView):
    serializer_class = PaperReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(paper__author=self.request.user).order_by(
            "-created_at"
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaperUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    http_method_names = ["get", "put", "patch", "head", "options"]

    def perform_update(self, serializer):
        # Ensure only the author can update the paper
        paper = self.get_object()
        if paper.author != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own papers.")
        serializer.save()


class PaperDeleteView(generics.DestroyAPIView):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def perform_destroy(self, instance):
        # Ensure only the author can delete the paper
        if instance.author != self.request.user:
            raise permissions.PermissionDenied("You can only delete your own papers.")

        # Delete associated files safely
        try:
            if instance.file and hasattr(instance.file, "url"):
                instance.file.delete(save=False)
            if hasattr(instance, "preview_file") and instance.preview_file:
                instance.preview_file.delete(save=False)
        except Exception as e:
            logger.error(f"Error deleting files for paper {instance.id}: {str(e)}")

        instance.delete()
