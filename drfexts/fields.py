import uuid
import warnings
from functools import partial
from django.contrib.postgres.fields import ArrayField as PGArrayField
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import CASCADE

from .constants import CommonStatus, AuditStatus
from .utils import get_serial_code

User = get_user_model()


class DefaultHelpTextMixin:
    def __init__(self, verbose_name, *args, **kwargs):
        kwargs.setdefault('help_text', verbose_name)
        super().__init__(verbose_name, *args, **kwargs)


class NullHelpTextMixin:
    def __init__(self, verbose_name, *args, **kwargs):
        kwargs['null'] = False
        kwargs.setdefault('help_text', verbose_name)
        super().__init__(verbose_name, *args, **kwargs)


class AutoField(models.AutoField):
    def __init__(self, verbose_name="主键", **kwargs):
        kwargs.setdefault('help_text', verbose_name)
        super().__init__(verbose_name, **kwargs)


class BigAutoField(DefaultHelpTextMixin, models.BigAutoField):
    pass


class CharField(NullHelpTextMixin, models.CharField):
    pass


class TextField(NullHelpTextMixin, models.TextField):
    pass


class IntegerField(DefaultHelpTextMixin, models.IntegerField):
    pass


class BigIntegerField(DefaultHelpTextMixin, models.BigIntegerField):
    pass


class SmallIntegerField(DefaultHelpTextMixin, models.SmallIntegerField):
    pass


class PositiveSmallIntegerField(DefaultHelpTextMixin, models.PositiveSmallIntegerField):
    pass


class BooleanField(DefaultHelpTextMixin, models.BooleanField):
    pass


class FileField(DefaultHelpTextMixin, models.FileField):
    pass


class ImageField(DefaultHelpTextMixin, models.ImageField):
    pass


class FloatField(DefaultHelpTextMixin, models.FloatField):
    pass


class DecimalField(DefaultHelpTextMixin, models.DecimalField):
    pass


class DateTimeField(DefaultHelpTextMixin, models.DateTimeField):
    pass


class DateField(DefaultHelpTextMixin, models.DateField):
    pass


class EmailField(DefaultHelpTextMixin, models.EmailField):
    pass


class URLField(DefaultHelpTextMixin, models.URLField):
    pass


class UUIDField(DefaultHelpTextMixin, models.UUIDField):
    pass


class JSONField(DefaultHelpTextMixin, models.JSONField):
    pass


class ArrayField(DefaultHelpTextMixin, PGArrayField):
    pass


class AutoUUIDField(models.UUIDField):
    def __init__(self, verbose_name="主键", **kwargs):
        kwargs['blank'] = True
        kwargs["default"] = uuid.uuid4
        kwargs.setdefault('help_text', verbose_name)
        kwargs.setdefault("primary_key", True)
        super().__init__(verbose_name, **kwargs)


class DefaultCodeField(models.CharField):
    """
    自动编号字段
    """

    DEFAULT_LENGTH = 15

    def __init__(self, verbose_name="编号", prefix="", **kwargs):
        kwargs['blank'] = True
        kwargs["default"] = partial(get_serial_code, prefix)
        kwargs["max_length"] = self.DEFAULT_LENGTH + len(prefix)
        kwargs['editable'] = False
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(verbose_name, **kwargs)


class DescriptionField(models.TextField):
    """
    description = DescriptionField()
    """

    def __init__(self, verbose_name="描述", **kwargs):
        kwargs.setdefault('blank', True)
        kwargs.setdefault('help_text', verbose_name)
        super().__init__(verbose_name, **kwargs)


class UserForeignKeyField(models.ForeignKey):
    """
    user = UserForeignKeyField()
    """

    def __init__(self, verbose_name="关联的用户", to=None, on_delete=None, **kwargs):
        to = to or User
        on_delete = on_delete or CASCADE
        kwargs.setdefault("db_constraint", False)
        kwargs.setdefault('help_text', verbose_name)
        super().__init__(to=to, verbose_name=verbose_name, on_delete=on_delete, **kwargs)


class UpdatedAtField(models.DateTimeField):
    """
    update_datetime = ModifyDateTimeField()
    """

    def __init__(self, verbose_name="修改时间", **kwargs):
        kwargs['editable'] = False
        kwargs['auto_now'] = True
        kwargs.setdefault('help_text', '该记录的最后修改时间')
        kwargs.setdefault('blank', True)
        super().__init__(verbose_name, **kwargs)


class CreatedAtField(models.DateTimeField):
    """
    create_datetime = CreateDateTimeField()
    """

    def __init__(self, verbose_name="创建时间", **kwargs):
        kwargs['editable'] = False
        kwargs['auto_now_add'] = True
        kwargs.setdefault('help_text', '该记录的创建时间')
        kwargs.setdefault('blank', True)
        super().__init__(verbose_name, **kwargs)


class CreatorField(models.ForeignKey):
    """
    creator = CreatorField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 128)
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('verbose_name', '创建者')
        kwargs.setdefault('help_text', '该记录的创建者')
        super().__init__(*args, **kwargs)


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


class StatusField(models.PositiveSmallIntegerField):
    """
    status = StatusField()
    """

    def __init__(self, verbose_name="状态", **kwargs):
        kwargs.setdefault('choices', CommonStatus.choices)
        kwargs.setdefault('default', CommonStatus.VALID)
        kwargs.setdefault('help_text', '该记录的状态')
        super().__init__(verbose_name, **kwargs)


class AuditStatusField(models.PositiveSmallIntegerField):
    """
    status = StatusField()
    """

    def __init__(self, verbose_name="审核状态", **kwargs):
        kwargs.setdefault('choices', AuditStatus.choices)
        kwargs.setdefault('null', True)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('help_text', '该记录的审核状态')
        super().__init__(verbose_name, **kwargs)


class VirtualForeignKey(models.ForeignKey):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        kwargs.setdefault("on_delete", models.CASCADE)
        kwargs.setdefault("db_constraint", False)

        if "related_name" not in kwargs:
            warnings.warn("建议设置related_name！")

        super().__init__(to, *args, **kwargs)


class OneToOneField(models.OneToOneField):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        kwargs.setdefault("on_delete", models.CASCADE)
        kwargs.setdefault("db_constraint", False)
        super().__init__(to, *args, **kwargs)


class VirtualManyToMany(models.ManyToManyField):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        if "through" not in kwargs:
            kwargs["db_constraint"] = False

        if "related_name" not in kwargs:
            warnings.warn("建议设置related_name！")

        super().__init__(to, *args, **kwargs)
