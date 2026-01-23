import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone


class Chat(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False)
    title = models.CharField(max_length=100, editable=False, verbose_name='Título')
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="chats")
    completed = models.BooleanField(default=False)

    # Campos de auditoria
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chats_created',
        verbose_name='Criado por'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chats_updated',
        verbose_name='Atualizado por'
    )

    class Meta:
        verbose_name = 'Entrevista'
        verbose_name_plural = 'Entrevistas'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['job', 'completed']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()
            self.title = f"Chat {self.job.title} - {self.uuid}"
            super().save(*args, **kwargs)
            # Cria mensagem inicial do sistema
            initial_prompt = settings.INITIAL_PROMPT_TEMPLATE
            initial_prompt = initial_prompt.replace("{job_title}", self.job.title)
            initial_prompt = initial_prompt.replace("{job_requirements}", self.job.requirements)
            initial_prompt = initial_prompt.replace("{job_responsibilities}", self.job.responsibilities)
            Message.objects.create(chat=self, role="system", content=initial_prompt)
        else:
            super().save(*args, **kwargs)


class Message(models.Model):
    ROLE_CHOICES = (
        ("system", "Sistema"),
        ("user", "Candidato"),
        ("assistant", "Ada")
    )

    chat = models.ForeignKey("interviews.Chat", on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=9, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} - {self.chat.title}"
