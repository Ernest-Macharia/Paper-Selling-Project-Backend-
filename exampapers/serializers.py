from rest_framework import serializers
from .models import Paper, Category, Course, School, Order


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class CourseSerializer(serializers.ModelSerializer):
    paper_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = Course
        fields = ['id', 'name', 'paper_count']


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = ['id', 'name']


class PaperSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    school = SchoolSerializer(read_only=True)
    document_url = serializers.SerializerMethodField()
    class Meta:
        model = Paper
        fields = '__all__'
        read_only_fields = ['author']

    def get_document_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url)
        return None
    

class OrderSerializer(serializers.ModelSerializer):
    paper = PaperSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'paper', 'price', 'status', 'created_at']
