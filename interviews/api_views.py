from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from core.utils import success_response, error_response
from core.permissions import IsAdminUser
from core.throttles import (
    InterviewCreateThrottle,
    InterviewMessageThrottle,
    InterviewDetailThrottle,
    InterviewMessageByUUIDThrottle,
)
from jobs.models import Job
from .models import Chat, Message
from .services import get_chat_service
from .exceptions import (
    AITimeoutError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseError,
    AIAuthenticationError,
    ChatCompletedError,
)
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
    Rate limit: 10 entrevistas por hora por IP.
    """
    permission_classes = [AllowAny]
    throttle_classes = [InterviewCreateThrottle]

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
    Rate limit: 120 requisições por hora por IP.
    """
    permission_classes = [AllowAny]
    throttle_classes = [InterviewDetailThrottle]

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
    Envia uma nova mensagem para a entrevista e obtém resposta da IA.
    Rate limit: 60 mensagens por hora por IP + limite por UUID de entrevista.
    """
    permission_classes = [AllowAny]
    throttle_classes = [InterviewMessageThrottle, InterviewMessageByUUIDThrottle]

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

        try:
            chat_service = get_chat_service()
            chat_service.process_user_message(chat, serializer.validated_data['content'])

            chat.refresh_from_db()
            chat_serializer = ChatSerializer(chat)

            return success_response(
                message="Mensagem enviada com sucesso",
                data=chat_serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        except ChatCompletedError:
            return error_response(
                message="Esta entrevista já foi finalizada",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except AITimeoutError:
            return error_response(
                message="O serviço de IA demorou muito para responder. Tente novamente.",
                errors=[{"code": "ai_timeout", "detail": "Timeout na comunicação com a IA"}],
                status_code=status.HTTP_504_GATEWAY_TIMEOUT
            )

        except AIConnectionError:
            return error_response(
                message="Não foi possível conectar ao serviço de IA. Tente novamente.",
                errors=[{"code": "ai_connection_error", "detail": "Erro de conexão com a IA"}],
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        except AIRateLimitError as e:
            return error_response(
                message="Serviço de IA temporariamente indisponível. Aguarde alguns minutos.",
                errors=[{"code": "ai_rate_limit", "detail": f"Rate limit atingido. Retry após {e.retry_after}s"}],
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )

        except AIAuthenticationError:
            return error_response(
                message="Erro interno de configuração. Contate o administrador.",
                errors=[{"code": "ai_auth_error", "detail": "Erro de autenticação com a IA"}],
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        except AIResponseError:
            return error_response(
                message="Resposta inesperada do serviço de IA. Tente novamente.",
                errors=[{"code": "ai_response_error", "detail": "Resposta inválida da IA"}],
                status_code=status.HTTP_502_BAD_GATEWAY
            )


class AdminInterviewListAPIView(generics.ListAPIView):
    """
    GET /api/v1/admin/interviews/
    Lista todas as entrevistas (somente admin).
    """
    queryset = Chat.objects.all().order_by('-created_at')
    serializer_class = ChatListSerializer
    permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            message="Entrevistas listadas com sucesso",
            data=serializer.data
        )
