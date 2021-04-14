import logging
import os
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.transaction import atomic


class CustomEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')

        return super().default(obj)


class MakeFileHandler(logging.FileHandler):
    def __init__(self, filename, mode="a", encoding=None, delay=0):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, mode, encoding, delay)


@atomic
def atomic_call(*funcs):
    """
    Call function atomicly
    """
    for func in funcs:
        if not callable(func):
            raise TypeError(f"{func} must be callable!")

        func()
