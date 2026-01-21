from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginLog(models.Model):
    """
    Modelo para registrar tentativas de login.
    """
    STATUS_CHOICES = (
        ('success', 'Sucesso'),
        ('failed', 'Falhou'),
        ('blocked', 'Bloqueado'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='login_logs',
        verbose_name='Usuário'
    )
    username = models.CharField(max_length=150, verbose_name='Username tentado')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Endereço IP')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='Status')
    message = models.CharField(max_length=255, blank=True, verbose_name='Mensagem')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora')

    class Meta:
        verbose_name = 'Log de Login'
        verbose_name_plural = 'Logs de Login'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"{self.username} - {self.status} - {self.created_at}"

    @classmethod
    def log_attempt(cls, request, username, status, message='', user=None):
        """
        Registra uma tentativa de login.
        """
        ip_address = cls.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        return cls.objects.create(
            user=user,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            message=message
        )

    @staticmethod
    def get_client_ip(request):
        """
        Obtém o IP real do cliente, considerando proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @classmethod
    def get_recent_failed_attempts(cls, username=None, ip_address=None, minutes=30):
        """
        Retorna o número de tentativas falhas recentes.
        """
        from django.utils import timezone
        from datetime import timedelta

        time_threshold = timezone.now() - timedelta(minutes=minutes)
        queryset = cls.objects.filter(
            status='failed',
            created_at__gte=time_threshold
        )

        if username:
            queryset = queryset.filter(username=username)
        if ip_address:
            queryset = queryset.filter(ip_address=ip_address)

        return queryset.count()
