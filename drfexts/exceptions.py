"""
Global exception and warning classes.
"""
import traceback

from django.conf import settings
from django.core.exceptions import PermissionDenied as _PermissionDenied, PermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from rest_framework.utils.serializer_helpers import ReturnList
from rest_framework.views import set_rollback


def _get_detail(detail):
    if isinstance(detail, list):
        return ''.join([x if isinstance(x, str) else _get_detail(x) for x in detail])
    result = ''
    for v in detail.values():
        result += _get_detail(v)
    return result


class BaseError(Exception):
    code = HTTP_500_INTERNAL_SERVER_ERROR
    params = None
    message = 'internal error'

    def __init__(self, message=None, detail=None, data=None):
        self.message = message or self.message
        super().__init__(self.message, self.code, self.params)


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, _PermissionDenied):
        exc = exceptions.PermissionDenied()

    headers = {}
    if isinstance(exc, exceptions.ValidationError):
        data = {"code": exc.status_code, 'message': exc.default_code, 'data': exc.detail}
    elif isinstance(exc, exceptions.APIException):
        # DRF异常处理
        code = exc.status_code
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait
        data = {"code": code, 'message': str(exc.detail), 'data': exc.detail}
    elif isinstance(exc, BaseError):
        # 自定义异常处理
        data = {"code": exc.code, "message": exc.message}
    else:
        data = {"code": HTTP_500_INTERNAL_SERVER_ERROR, "message": "Internal Error", "data": getattr(exc, 'message', repr(exc))}

    set_rollback()
    if settings.DEBUG:
        traceback.print_exc()
        data.update(traceback=traceback.format_exc())
    return Response(data, status=HTTP_200_OK, headers=headers)


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, exceptions.APIException):
        headers = {}
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['Retry-After'] = '%d' % exc.wait

        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        set_rollback()
        resp = Response(data, status=status.HTTP_200_OK, headers=headers)
        resp.error_code = exc.status_code
        return resp

    return None
