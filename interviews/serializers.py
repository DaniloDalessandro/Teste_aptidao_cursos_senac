from rest_framework import serializers
from .models import Chat, Message
from jobs.serializers import JobListSerializer


class MessageSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'role', 'role_display', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        required=True,
        allow_blank=False,
        min_length=2,
        max_length=2000,
        error_messages={
            'blank': 'A mensagem não pode estar vazia.',
            'min_length': 'A mensagem deve ter pelo menos 2 caracteres.',
            'max_length': 'A mensagem não pode exceder 2000 caracteres.',
        }
    )

    def validate_content(self, value):
        """Valida e sanitiza o conteúdo da mensagem."""
        content = value.strip()
        if not content:
            raise serializers.ValidationError("A mensagem não pode estar vazia.")
        return content


class ChatSerializer(serializers.ModelSerializer):
    """Serializer completo do Chat com mensagens."""
    messages = MessageSerializer(many=True, read_only=True)
    job = JobListSerializer(read_only=True)

    class Meta:
        model = Chat
        fields = ['uuid', 'title', 'job', 'completed', 'messages']
        read_only_fields = ['uuid', 'title', 'completed']


class ChatListSerializer(serializers.ModelSerializer):
    """Serializer leve para listagem de chats (admin)."""
    job_title = serializers.CharField(source='job.title', read_only=True)
    messages_count = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True, default=None)

    class Meta:
        model = Chat
        fields = [
            'uuid', 'title', 'job_title', 'completed', 'messages_count',
            'created_at', 'updated_at', 'created_by_username', 'updated_by_username'
        ]

    def get_messages_count(self, obj):
        return obj.messages.count()


class InterviewCreateSerializer(serializers.Serializer):
    job_id = serializers.IntegerField(required=True)

    def validate_job_id(self, value):
        from jobs.models import Job
        if not Job.objects.filter(id=value).exists():
            raise serializers.ValidationError("Curso não encontrado")
        return value
