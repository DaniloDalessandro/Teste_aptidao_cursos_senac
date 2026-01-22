from django.http import HttpResponseNotAllowed
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from jobs.models import Job
from .models import Chat
from .services import ChatService
from .exceptions import (
    AITimeoutError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseError,
    AIAuthenticationError,
    ChatCompletedError,
)


def create(request, job_pk):
    if request.method == "POST":
        job = get_object_or_404(Job, pk=job_pk)
        service = ChatService()
        chat = service.create_chat(job)
        return redirect("interviews:details", uuid=chat.uuid)
    return HttpResponseNotAllowed(permitted_methods=("POST",))


def details(request, uuid):
    chat = get_object_or_404(
        Chat.objects.prefetch_related('messages'),
        uuid=uuid
    )
    return render(
        request,
        "interviews/details.html",
        {
            "page_title": f"Entrevista para: {chat.job.title}",
            "chat": chat,
        }
    )


def create_message(request, chat_uuid):
    if request.method == "POST":
        chat = get_object_or_404(Chat, uuid=chat_uuid)

        if chat.completed:
            messages.warning(request, "Esta entrevista já foi concluída.")
            return redirect("interviews:details", uuid=chat_uuid)

        answer = request.POST.get("answer", "").strip()

        if not answer:
            messages.error(request, "Por favor, digite uma resposta.")
            return redirect("interviews:details", uuid=chat_uuid)

        if len(answer) > 2000:
            messages.error(request, "Resposta muito longa. Máximo 2000 caracteres.")
            return redirect("interviews:details", uuid=chat_uuid)

        try:
            service = ChatService()
            service.process_user_message(chat, answer)

        except ChatCompletedError:
            messages.warning(request, "Esta entrevista já foi concluída.")

        except AITimeoutError:
            messages.error(
                request,
                "O serviço de IA demorou muito para responder. Por favor, tente novamente."
            )

        except AIRateLimitError as e:
            messages.error(
                request,
                f"Muitas requisições. Por favor, aguarde {e.retry_after} segundos e tente novamente."
            )

        except AIAuthenticationError:
            messages.error(
                request,
                "Erro de configuração do sistema. Por favor, contate o administrador."
            )

        except AIConnectionError:
            messages.error(
                request,
                "Erro de conexão com o serviço de IA. Por favor, tente novamente."
            )

        except AIResponseError:
            messages.error(
                request,
                "Resposta inesperada do serviço de IA. Por favor, tente novamente."
            )

        except Exception:
            messages.error(
                request,
                "Ocorreu um erro inesperado. Por favor, tente novamente."
            )

        return redirect("interviews:details", uuid=chat_uuid)
    return HttpResponseNotAllowed(permitted_methods=("POST",))
