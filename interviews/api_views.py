from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from core.utils import success_response, error_response
from core.permissions import IsAdminUser
from jobs.models import Job
from .models import Chat, Message
from .serializers import (
    ChatSerializer,
    ChatListSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    InterviewCreateSerializer,
)


class InterviewCreateAPIView(APIView):
    """
    POST /api/v1/interviews/
    Cria uma nova entrevista (chat) para um curso.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InterviewCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Dados inválidos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        job_id = serializer.validated_data['job_id']
        job = Job.objects.get(id=job_id)

        chat = Chat.objects.create(job=job)

        chat_serializer = ChatSerializer(chat)
        return success_response(
            message="Entrevista criada com sucesso",
            data=chat_serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class InterviewDetailAPIView(APIView):
    """
    GET /api/v1/interviews/{uuid}/
    Retorna os detalhes de uma entrevista específica.
    """
    permission_classes = [AllowAny]

    def get(self, request, uuid):
        try:
            chat = Chat.objects.get(uuid=uuid)
            serializer = ChatSerializer(chat)
            return success_response(
                message="Entrevista encontrada",
                data=serializer.data
            )
        except Chat.DoesNotExist:
            return error_response(
                message="Entrevista não encontrada",
                status_code=status.HTTP_404_NOT_FOUND
            )


class InterviewMessageCreateAPIView(APIView):
    """
    POST /api/v1/interviews/{uuid}/messages/
    Envia uma nova mensagem para a entrevista.
    """
    permission_classes = [AllowAny]

    def post(self, request, uuid):
        try:
            chat = Chat.objects.get(uuid=uuid)
        except Chat.DoesNotExist:
            return error_response(
                message="Entrevista não encontrada",
                status_code=status.HTTP_404_NOT_FOUND
            )

        if chat.completed:
            return error_response(
                message="Esta entrevista já foi finalizada",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = MessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Dados inválidos",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        message = Message.objects.create(
            chat=chat,
            role="user",
            content=serializer.validated_data['content']
        )

        chat.refresh_from_db()
        chat_serializer = ChatSerializer(chat)

        return success_response(
            message="Mensagem enviada com sucesso",
            data=chat_serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class AdminInterviewListAPIView(generics.ListAPIView):
    """
    GET /api/v1/admin/interviews/
    Lista todas as entrevistas (somente admin).
    """
    queryset = Chat.objects.all().order_by('-uuid')
    serializer_class = ChatListSerializer
    permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            message="Entrevistas listadas com sucesso",
            data=serializer.data
        )
