import django_filters
from django.db.models import Avg, Count, Q
from .models import Paper

class PaperFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name='category__id', lookup_expr='exact')
    course = django_filters.NumberFilter(field_name='course__id', lookup_expr='exact')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    is_free = django_filters.BooleanFilter(field_name='is_free')
    has_reviews = django_filters.BooleanFilter(method='filter_has_reviews')
    min_average_rating = django_filters.NumberFilter(method='filter_min_average_rating')

    class Meta:
        model = Paper
        fields = ['category', 'course', 'is_free']

    def filter_has_reviews(self, queryset, name, value):
        if value:
            return queryset.annotate(num_reviews=Count('reviews')).filter(num_reviews__gt=0)
        return queryset

    def filter_min_average_rating(self, queryset, name, value):
        return queryset.annotate(avg_rating=Avg('reviews__rating')).filter(avg_rating__gte=value)
