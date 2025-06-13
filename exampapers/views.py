from django.db.models import (
    Count, Avg, Q
)
from rest_framework import generics, permissions, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (
    PaperSerializer, CategorySerializer,
    CourseSerializer, SchoolSerializer,
    OrderSerializer, CheckoutInitiateSerializer
)

from .models import (
    Paper, Category, Course, Payment,
    School, Order, Review, Wishlist
)
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.timezone import now
from django.db.models import Count, Sum, Avg
from users.models import User


class PaperFilterMixin:
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'course', 'school', 'status', 'is_free']
    search_fields = ['title', 'description', 'author__username', 'category__name', 'course__name', 'school__name']
    ordering_fields = [
        'title', 'upload_date', 'downloads', 'views',
        'price', 'earnings', 'category__name', 'course__name', 'school__name'
    ]
    ordering = ['-upload_date']


class AllPapersView(PaperFilterMixin, generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Only published papers, can add filtering and searching from mixin
        return Paper.objects.filter(status="published").select_related('category', 'course', 'school')


class UserUploadsView(generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(author=self.request.user).select_related('category', 'course', 'school')


class UserDownloadsView(generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(
            order__user=self.request.user).distinct().select_related(
                'category', 'course', 'school')
    

class PaperDetailView(generics.RetrieveAPIView):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class PaperUploadView(generics.CreateAPIView):
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Category.objects.annotate(
            paper_count=Count('papers', filter=Q(papers__status='published')),
            average_price=Avg('papers__price', filter=Q(papers__status='published')),
            average_rating=Avg('papers__reviews__rating')
        ).order_by('-paper_count')

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'paper_count', 'average_price', 'average_rating']
    ordering = ['-paper_count']


class CourseListView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Course.objects.annotate(
            paper_count=Count('papers', filter=Q(papers__status='published')),
            average_price=Avg('papers__price', filter=Q(papers__status='published')),
            average_rating=Avg('papers__reviews__rating')
        ).order_by('-paper_count')

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'paper_count', 'average_price', 'average_rating']
    ordering = ['-paper_count']


class PopularCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Popular by number of published papers only
        return Course.objects.annotate(
            paper_count=Count('papers', filter=Q(papers__status='published'))
        ).order_by('-paper_count')[:10]
    

class PopularCategoriesView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        # Popular by number of published papers only
        return Category.objects.annotate(
            paper_count=Count('papers', filter=Q(papers__status='published'))
        ).order_by('-paper_count')[:10]


class SchoolListView(generics.ListAPIView):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]


class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

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
    permission_classes = [permissions.IsAuthenticated]  # Only for logged-in users

    def get(self, request):
        user = request.user
        today = now().date()

        # 🌐 Global Statistics
        total_users = User.objects.count()
        total_papers = Paper.objects.filter(status="published").count()
        total_downloads = Paper.objects.aggregate(total=Sum('downloads'))['total'] or 0
        total_uploads = Paper.objects.aggregate(total=Sum('uploads'))['total'] or 0
        total_views = Paper.objects.aggregate(total=Sum('views'))['total'] or 0
        total_earnings = Paper.objects.aggregate(total=Sum('earnings'))['total'] or 0
        total_orders = Order.objects.count()
        completed_orders = Order.objects.filter(status="completed").count()
        new_users_today = User.objects.filter(date_joined__date=today).count()
        papers_uploaded_today = Paper.objects.filter(upload_date__date=today).count()

        # 👤 User-specific Stats
        user_papers = Paper.objects.filter(author=user)
        user_downloads = user_papers.aggregate(total=Sum('downloads'))['total'] or 0
        user_views = user_papers.aggregate(total=Sum('views'))['total'] or 0
        user_earnings = user_papers.aggregate(total=Sum('earnings'))['total'] or 0
        user_paper_count = user_papers.count()
        user_orders = Order.objects.filter(user=user).count()
        user_completed_orders = Order.objects.filter(user=user, status="completed").count()
        user_reviews = Review.objects.filter(user=user).count()
        user_wishlist_count = Wishlist.objects.filter(user=user).count()

        return Response({
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
            "user_papers_uploaded": user_paper_count,
            "user_total_downloads": user_downloads,
            "user_total_views": user_views,
            "user_total_earnings": float(user_earnings),
            "user_orders": user_orders,
            "user_completed_orders": user_completed_orders,
            "user_review_count": user_reviews,
            "user_wishlist_count": user_wishlist_count,
        })


class CheckoutInitiateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutInitiateSerializer(data=request.data)
        if serializer.is_valid():
            paper_id = serializer.validated_data["paper_id"]
            payment_method = serializer.validated_data["payment_method"]
            user = request.user

            try:
                paper = Paper.objects.get(id=paper_id)
            except Paper.DoesNotExist:
                return Response({"error": "Paper not found."}, status=status.HTTP_404_NOT_FOUND)

            # Create Order
            order = Order.objects.create(
                user=user,
                paper=paper,
                price=paper.price,
                status="pending"
            )

            # Create initial Payment record (optional)
            payment = Payment.objects.create(
                order=order,
                payment_method=payment_method,
                transaction_id=f"TEMP-{order.id}",  # Placeholder, replace after real payment
                amount=paper.price
            )

            # Return mock payment URL or instructions
            return Response({
                "message": "Order initiated.",
                "order_id": order.id,
                "payment_method": payment_method,
                "payment_url": f"/mock-payments/{payment_method}/{order.id}/"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
