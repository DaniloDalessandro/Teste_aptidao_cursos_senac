from django.urls import path
from .api_views import JobListAPIView, JobDetailAPIView

urlpatterns = [
    path('', JobListAPIView.as_view(), name='api-job-list'),
    path('<int:pk>/', JobDetailAPIView.as_view(), name='api-job-detail'),
]
