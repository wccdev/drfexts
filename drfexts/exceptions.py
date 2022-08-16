"""
Global exception and warning classes.
"""
import traceback

from django.conf import settings
from rest_framework.response import Response
from rest_framework.status import HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.views import exception_handler, set_rollback


def _get_detail(detail):
    if isinstance(detail, list):
        return "".join([x if isinstance(x, str) else _get_detail(x) for x in detail])
    result = ""
    for v in detail.values():
        result += _get_detail(v)
    return result


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Catch other exceptions.
    if response is None:
        response = Response({"detail": str(exc)}, status=HTTP_500_INTERNAL_SERVER_ERROR)
        set_rollback()
        if settings.DEBUG:
            traceback.print_exc()
            response.data.update(traceback=traceback.format_exc())

    return response
