import uuid
from functools import partial

from django.conf import settings
from django.contrib.contenttypes import fields as ct_fields
from django.contrib.postgres.fields import ArrayField as PGArrayField
from django.core import checks
from django.db import models
from django.db.models import CASCADE
from django_currentuser.db.models import CurrentUserField

from .choices import SimpleStatus
from .constants import AuditStatus, CommonStatus
from .utils import get_serial_code


class DefaultHelpTextMixin:
    def __init__(self, verbose_name, *args, **kwargs):
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(verbose_name, *args, **kwargs)


class NullHelpTextMixin:
    def __init__(self, verbose_name, *args, **kwargs):
        kwargs["null"] = False
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(verbose_name, *args, **kwargs)


class RelatedNameCheckMixin:
    def check(self, **kwargs):
        return [
            *super().check(**kwargs),  # noqa
            *self._check_related_name(),
        ]

    def _check_related_name(self, **kwargs):
        return (
            [
                checks.Warning(
                    "Setting 'related_name' on a RelatedField may be better!",
                    obj=self,
                )
            ]
            if self.remote_field.related_name is None
            else []
        )  # noqa


class AutoField(models.AutoField):
    def __init__(self, verbose_name="主键", **kwargs):
        kwargs.setdefault("help_text", verbose_name)
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


class FilePathField(DefaultHelpTextMixin, models.FilePathField):
    pass


class FloatField(DefaultHelpTextMixin, models.FloatField):
    pass


class DecimalField(DefaultHelpTextMixin, models.DecimalField):
    pass


class DateTimeField(DefaultHelpTextMixin, models.DateTimeField):
    pass


class DateField(DefaultHelpTextMixin, models.DateField):
    pass


class TimeField(DefaultHelpTextMixin, models.TimeField):
    pass


class DurationField(DefaultHelpTextMixin, models.DurationField):
    pass


class EmailField(DefaultHelpTextMixin, models.EmailField):
    pass


class URLField(DefaultHelpTextMixin, models.URLField):
    pass


class IPAddressField(DefaultHelpTextMixin, models.IPAddressField):
    pass


class UUIDField(DefaultHelpTextMixin, models.UUIDField):
    pass


class JSONField(DefaultHelpTextMixin, models.JSONField):
    pass


class ArrayField(PGArrayField):
    def __init__(self, verbose_name, base_field, **kwargs):
        kwargs.setdefault("help_text", verbose_name)
        kwargs.setdefault("verbose_name", verbose_name)
        super().__init__(base_field, **kwargs)


class AutoUUIDField(models.UUIDField):
    def __init__(self, verbose_name="主键", **kwargs):
        kwargs["blank"] = True
        kwargs["default"] = uuid.uuid4
        kwargs.setdefault("help_text", verbose_name)
        kwargs.setdefault("primary_key", True)
        super().__init__(verbose_name, **kwargs)


class DefaultCodeField(models.CharField):
    """
    自动编号字段
    """

    DEFAULT_LENGTH = 15

    def __init__(self, verbose_name="编号", prefix="", **kwargs):
        self.prefix = prefix
        kwargs["blank"] = True
        kwargs["default"] = partial(get_serial_code, prefix)
        kwargs["max_length"] = self.DEFAULT_LENGTH + len(prefix)
        kwargs["editable"] = False
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(verbose_name, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        # Only include kwarg if it's not the default
        if self.prefix != "":
            kwargs["prefix"] = self.prefix
        return name, path, args, kwargs


class DescriptionField(models.TextField):
    """
    description = DescriptionField()
    """

    def __init__(self, verbose_name="描述", **kwargs):
        kwargs.setdefault("blank", True)
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(verbose_name, **kwargs)


class UserForeignKeyField(models.ForeignKey):
    """
    user = UserForeignKeyField()
    """

    def __init__(self, verbose_name="关联的用户", to=None, on_delete=None, **kwargs):
        to = to or settings.AUTH_USER_MODEL
        on_delete = on_delete or CASCADE
        kwargs.setdefault("db_constraint", False)
        kwargs.setdefault("help_text", verbose_name)
        super().__init__(to=to, verbose_name=verbose_name, on_delete=on_delete, **kwargs)


class UpdatedAtField(models.DateTimeField):
    """
    update_datetime = ModifyDateTimeField()
    """

    def __init__(self, verbose_name="修改时间", **kwargs):
        kwargs["editable"] = False
        kwargs["auto_now"] = True
        kwargs.setdefault("help_text", "该记录的最后修改时间")
        kwargs.setdefault("blank", True)
        super().__init__(verbose_name, **kwargs)


class CreatedAtField(models.DateTimeField):
    """
    create_datetime = CreateDateTimeField()
    """

    def __init__(self, verbose_name="创建时间", **kwargs):
        kwargs["editable"] = False
        kwargs["auto_now_add"] = True
        kwargs.setdefault("help_text", "该记录的创建时间")
        kwargs.setdefault("blank", True)
        super().__init__(verbose_name, **kwargs)


class CreatedByField(CurrentUserField):
    """
    created_by = CreatedByField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("verbose_name", "创建人")
        kwargs.setdefault("editable", False)
        kwargs.setdefault("help_text", "该记录的创建者")
        kwargs.setdefault("related_name", "%(class)s_created_by")
        kwargs.setdefault("on_delete", models.CASCADE)
        kwargs["db_constraint"] = False
        super().__init__(*args, **kwargs)

    def _warn_for_shadowing_args(self, *args, **kwargs):
        pass


class UpdatedByField(CurrentUserField):
    """
    updated_by = UpdatedByField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("on_update", True)
        kwargs.setdefault("verbose_name", "修改人")
        kwargs.setdefault("help_text", "该记录的修改人")
        kwargs.setdefault("related_name", "%(class)s_updated_by")
        kwargs.setdefault("on_delete", models.CASCADE)
        kwargs["db_constraint"] = False
        super().__init__(*args, **kwargs)

    def _warn_for_shadowing_args(self, *args, **kwargs):
        pass


class CreatorCharField(models.CharField):
    """
    creator = CreatorCharField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 128)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("verbose_name", "创建者")
        kwargs.setdefault("help_text", "该记录的创建者")
        super().__init__(*args, **kwargs)


class ModifierCharField(models.CharField):
    """
    modifier = ModifierCharField()
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 128)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("verbose_name", "修改者")
        kwargs.setdefault("help_text", "该记录最后修改者")
        super().__init__(*args, **kwargs)


class StatusField(models.PositiveSmallIntegerField):
    """
    status = StatusField()
    """

    def __init__(self, verbose_name="状态", **kwargs):
        kwargs.setdefault("choices", CommonStatus.choices)
        kwargs.setdefault("default", CommonStatus.VALID)
        kwargs.setdefault("help_text", "100：已失效，75：待失效，50：有效，25：暂停中，10：待生效，5：待提交，0：删除")
        super().__init__(verbose_name, **kwargs)


class SimpleStatusField(models.PositiveSmallIntegerField):
    """
    status = SimpleStatusField()
    """

    def __init__(self, verbose_name="状态", **kwargs):
        kwargs.setdefault("choices", SimpleStatus.choices)
        kwargs.setdefault("default", SimpleStatus.VALID)
        kwargs.setdefault("help_text", "100：已失效，50：生效中")
        super().__init__(verbose_name, **kwargs)


class AuditStatusField(models.PositiveSmallIntegerField):
    """
    status = StatusField()
    """

    def __init__(self, verbose_name="审核状态", **kwargs):
        kwargs.setdefault("choices", AuditStatus.choices)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("help_text", "该记录的审核状态")
        super().__init__(verbose_name, **kwargs)


class VirtualForeignKey(models.ForeignKey):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        kwargs["db_constraint"] = False

        if kwargs.get("null"):
            kwargs.setdefault("blank", True)
            kwargs.setdefault("on_delete", models.SET_NULL)
        else:
            kwargs.setdefault("on_delete", models.CASCADE)

        super().__init__(to, *args, **kwargs)


class OneToOneField(models.OneToOneField):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        kwargs["db_constraint"] = False

        if kwargs.get("null"):
            kwargs.setdefault("blank", True)
            kwargs.setdefault("on_delete", models.SET_NULL)
        else:
            kwargs.setdefault("on_delete", models.CASCADE)

        super().__init__(to, *args, **kwargs)


class VirtualManyToMany(models.ManyToManyField):
    def __init__(self, verbose_name, to, *args, **kwargs):
        kwargs.setdefault("verbose_name", verbose_name)
        if "through" not in kwargs:
            kwargs["db_constraint"] = False

        super().__init__(to, *args, **kwargs)


class GenericForeignKey(ct_fields.GenericForeignKey):
    def __init__(
        self, ct_field="content_type", fk_field="object_id", for_concrete_model=True
    ):
        super().__init__(
            ct_field=ct_field, fk_field=fk_field, for_concrete_model=for_concrete_model
        )


class GenericRelation(ct_fields.GenericRelation):
    def __init__(
        self,
        verbose_name,
        to,
        object_id_field="object_id",
        content_type_field="content_type",
        for_concrete_model=True,
        related_query_name=None,
        limit_choices_to=None,
        **kwargs,
    ):
        super().__init__(
            to,
            object_id_field=object_id_field,
            content_type_field=content_type_field,
            for_concrete_model=for_concrete_model,
            related_query_name=related_query_name,
            limit_choices_to=limit_choices_to,
            verbose_name=verbose_name,
            **kwargs,
        )
