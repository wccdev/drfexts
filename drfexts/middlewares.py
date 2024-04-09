import threading

from django.utils import timezone

_thread_locals = threading.local()


class RequestTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            _thread_locals.request_time = timezone.now()
            response = self.get_response(request)
        finally:
            _thread_locals.request_time = None

        return response


def get_request_time():
    return getattr(_thread_locals, "request_time", timezone.now())
