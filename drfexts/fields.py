import uuid
from functools import partial

from django.conf import settings
from django.db import models
from django.db.models import SET_NULL

from .utils import get_serial_code


class AutoUUIDField(models.UUIDField):

    def __init__(self, **kwargs):
        kwargs['blank'] = True
        kwargs["default"] = uuid.uuid4
        kwargs.setdefault("primary_key", True)
        kwargs.setdefault("verbose_name", "主键")
        super().__init__(**kwargs)


class DefaultCodeField(models.CharField):
    """
    自动编号字段
    """
    DEFAULT_LENGTH = 15

    def __init__(self, prefix="", **kwargs):
        kwargs['blank'] = True
        kwargs["default"] = partial(get_serial_code, prefix)
        kwargs["max_length"] = self.DEFAULT_LENGTH + len(prefix)
        kwargs['editable'] = False
        kwargs.setdefault("verbose_name", "编号")
        kwargs.setdefault("help_text", kwargs["verbose_name"])
        super().__init__(**kwargs)


class DescriptionField(models.TextField):
    """
    description = DescriptionField()
    """

    def __init__(self, *args, **kwargs):
        if kwargs.get('null', True):
            kwargs['default'] = kwargs.get('default', '')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        kwargs.setdefault('verbose_name', '描述')
        kwargs.setdefault('help_text', kwargs['verbose_name'])
        super().__init__(*args, **kwargs)


class UserForeignKeyField(models.ForeignKey):
    """
    user = UserForeignKeyField()
    """

    def __init__(self, to=None, on_delete=None, **kwargs):
        to = to or settings.AUTH_USER_MODEL
        on_delete = on_delete or SET_NULL
        kwargs.setdefault("to_field", "id")
        kwargs.setdefault("db_constraint", False)
        kwargs.setdefault('verbose_name', '关联的用户')
        kwargs.setdefault('help_text', kwargs['verbose_name'])
        super().__init__(to=to, on_delete=on_delete, **kwargs)


class UpdatedAtField(models.DateTimeField):
    """
    update_datetime = ModifyDateTimeField()
    """

    def __init__(self, verbose_name=None, name=None, auto_now=True, auto_now_add=False, **kwargs):
        verbose_name = verbose_name or '修改时间'
        kwargs['editable'] = kwargs.get('default', False)
        kwargs.setdefault('help_text', '修改时间')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super().__init__(verbose_name, name, auto_now, auto_now_add, **kwargs)


class CreatedAtField(models.DateTimeField):
    """
    create_datetime = CreateDateTimeField()
    """

    def __init__(self, verbose_name=None, name=None, auto_now=False, auto_now_add=True, **kwargs):
        verbose_name = verbose_name or '创建时间'
        kwargs['editable'] = kwargs.get('default', False)
        kwargs.setdefault('help_text', '创建时间')
        kwargs.setdefault('blank', True)
        kwargs.setdefault('null', True)
        super().__init__(verbose_name, name, auto_now, auto_now_add, **kwargs)


class CreatorCharField(models.CharField):
    """
    creator = CreatorCharField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 128)
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('verbose_name', '创建者')
        kwargs.setdefault('help_text', '该记录的创建者')
        super().__init__(*args, **kwargs)


class ModifierCharField(models.CharField):
    """
    modifier = ModifierCharField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 128)
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('verbose_name', '修改者')
        kwargs.setdefault('help_text', '该记录最后修改者')
        super().__init__(*args, **kwargs)

