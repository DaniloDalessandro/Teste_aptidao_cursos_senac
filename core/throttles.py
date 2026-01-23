from rest_framework.throttling import SimpleRateThrottle


class InterviewCreateThrottle(SimpleRateThrottle):
    """
    Limita a criação de novas entrevistas por IP.
    Previne abuso na criação de múltiplas entrevistas.
    """
    scope = 'interview_create'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class InterviewMessageThrottle(SimpleRateThrottle):
    """
    Limita o envio de mensagens por IP.
    Previne spam e abuso da API de IA.
    """
    scope = 'interview_message'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class InterviewDetailThrottle(SimpleRateThrottle):
    """
    Limita consultas de detalhes de entrevistas por IP.
    """
    scope = 'interview_detail'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request)
        }


class InterviewMessageByUUIDThrottle(SimpleRateThrottle):
    """
    Limita mensagens por UUID de entrevista.
    Impede envio excessivo de mensagens em uma única entrevista.
    """
    scope = 'interview_message'

    def get_cache_key(self, request, view):
        uuid = view.kwargs.get('uuid', '')
        return self.cache_format % {
            'scope': f'{self.scope}_uuid',
            'ident': uuid
        }
