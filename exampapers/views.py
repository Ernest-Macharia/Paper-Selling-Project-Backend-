from django.db.models import Count
from rest_framework import generics, permissions
from .serializers import PaperSerializer, CategorySerializer, CourseSerializer, SchoolSerializer
from .models import Paper, Category, Course, School


class AllPapersView(generics.ListAPIView):
    queryset = Paper.objects.filter(status="published")
    serializer_class = PaperSerializer
    permission_classes = [permissions.AllowAny]


class UserUploadsView(generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(author=self.request.user)


class UserDownloadsView(generics.ListAPIView):
    serializer_class = PaperSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Paper.objects.filter(order__user=self.request.user).distinct()
    

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
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]


class PopularCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Course.objects.annotate(paper_count=Count('paper')).order_by('-paper_count')[:10]


class SchoolListView(generics.ListAPIView):
    queryset = School.objects.all()
    serializer_class = SchoolSerializer
    permission_classes = [permissions.IsAuthenticated]
