import logging
import os
import random
from collections import OrderedDict
from datetime import datetime

from django.core.serializers.json import DjangoJSONEncoder
from django.db.transaction import atomic
from django.utils import timezone


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


def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


def get_serial_code(prefix=""):
    """
    生成序列号
    """
    random_number = random.randint(0, 999)
    return timezone.now().strftime(f"{prefix}%y%m%d%H%M%I{random_number:03d}")


def to_table_choices(choices: OrderedDict):
    """
    转换为前端适配的options
    """
    return [{"label": label, "value": value} for value, label in choices.items()]
