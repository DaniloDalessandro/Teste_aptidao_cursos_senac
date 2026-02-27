from django.contrib import admin

from .models import Chat, Message, InterviewResult


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


class InterviewResultInline(admin.StackedInline):
    model = InterviewResult
    extra = 0
    readonly_fields = ('finished_at', 'created_at')


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("title", "job", "completed")
    inlines = (MessageInline, InterviewResultInline)


@admin.register(InterviewResult)
class InterviewResultAdmin(admin.ModelAdmin):
    list_display = ("chat", "finished_at", "created_at")
    list_filter = ("finished_at",)
    search_fields = ("chat__title", "profile_summary")
    readonly_fields = ("finished_at", "created_at")
