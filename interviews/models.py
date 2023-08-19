import uuid

from django.db import models
from django.conf import settings


# Create your models here.

class Chat(models.Model):
    uuid = models.UUIDField(primary_key=True, editable=False)
    title = models.CharField(max_length=100, editable=False,verbose_name='Título')
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="chats")
    completed = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.uuid:
            self.uuid = uuid.uuid4()
            self.title = f"Chat {self.job.title} - {self.uuid}"
            super().save(*args, **kwargs)
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

    def __str__(self):
        return f"{self.role} - {self.chat.title}"
    
    def save(self, *args, **kwargs):
        if not self.pk and self.role != "assistant" and not self.chat.completed:
            super().save(*args, **kwargs)

            if self.role == "user" and self.chat.messages.filter(role="assistant").count() == 5:
                Message.objects.create(
                    chat=self.chat,
                    role="system",
                    content="Realize o feedback do candidato ao curso, esse feedback deve indicar quais os pontos positivos, os pontos negativos e o que deve ser melhorado, e de acordo com as respostas mensurar um porcentagem de aderência a vaga que vai de 0 a 100, e caso o candidato não tenha conhecimento em informatica basica, indicar o curo de introdução a informatica do senac. "
                )
                self.chat.completed = True
                self.chat.save()
            else:
                from .services import GptService
                service = GptService()
                Message.objects.create(
                    chat=self.chat,
                    role="assistant",
                    content=service.get_chat_completion(self.chat.messages.all())
                )
        else:
            super().save(*args, **kwargs)
