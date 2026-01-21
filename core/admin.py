from django.contrib import admin
from .models import LoginLog


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ['username', 'status', 'ip_address', 'created_at', 'user']
    list_filter = ['status', 'created_at']
    search_fields = ['username', 'ip_address', 'user__username']
    readonly_fields = ['user', 'username', 'ip_address', 'user_agent', 'status', 'message', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
