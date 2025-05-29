from django.db.models import (
    Count, Avg, Q
)
from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .serializers import (
    PaperSerializer, CategorySerializer,
    CourseSerializer, SchoolSerializer, OrderSerializer,
)

from .models import Paper, Category, Course, School, Order


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
