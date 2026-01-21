from django.urls import path, include
from .api_views import (
    LoginAPIView,
    TokenRefreshAPIView,
    TokenVerifyAPIView,
    LogoutAPIView,
    PasswordForgotAPIView,
    MeAPIView,
)
from interviews.api_urls import admin_urlpatterns as interviews_admin_urls

urlpatterns = [
    # Auth
    path('auth/login/', LoginAPIView.as_view(), name='api-auth-login'),
    path('auth/token/refresh/', TokenRefreshAPIView.as_view(), name='api-auth-token-refresh'),
    path('auth/token/verify/', TokenVerifyAPIView.as_view(), name='api-auth-token-verify'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-auth-logout'),
    path('auth/password/forgot/', PasswordForgotAPIView.as_view(), name='api-auth-password-forgot'),
    path('auth/me/', MeAPIView.as_view(), name='api-auth-me'),

    # Jobs
    path('jobs/', include('jobs.api_urls')),

    # Interviews
    path('interviews/', include('interviews.api_urls')),

    # Admin (protegido pelo middleware)
    path('admin/', include(interviews_admin_urls)),
]
