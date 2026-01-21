from django.urls import path
from .api_views import (
    InterviewCreateAPIView,
    InterviewDetailAPIView,
    InterviewMessageCreateAPIView,
    AdminInterviewListAPIView,
)

urlpatterns = [
    path('', InterviewCreateAPIView.as_view(), name='api-interview-create'),
    path('<uuid:uuid>/', InterviewDetailAPIView.as_view(), name='api-interview-detail'),
    path('<uuid:uuid>/messages/', InterviewMessageCreateAPIView.as_view(), name='api-interview-message'),
]

admin_urlpatterns = [
    path('interviews/', AdminInterviewListAPIView.as_view(), name='api-admin-interview-list'),
]
