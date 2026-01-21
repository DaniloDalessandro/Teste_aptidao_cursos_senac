from rest_framework import generics
from rest_framework.permissions import AllowAny

from core.utils import success_response, error_response
from .models import Job
from .serializers import JobSerializer, JobListSerializer


class JobListAPIView(generics.ListAPIView):
    """
    GET /api/v1/jobs/
    Lista todos os cursos disponíveis.
    """
    queryset = Job.objects.all()
    serializer_class = JobListSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            message="Cursos listados com sucesso",
            data=serializer.data
        )


class JobDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/v1/jobs/{id}/
    Retorna os detalhes de um curso específico.
    """
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return success_response(
                message="Curso encontrado",
                data=serializer.data
            )
        except Job.DoesNotExist:
            return error_response(
                message="Curso não encontrado",
                status_code=404
            )
