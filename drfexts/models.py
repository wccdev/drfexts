from itertools import chain

from django.db import models
from django.db.models import Func, fields

from .constants import CommonStatus
from .fields import (
    AutoUUIDField,
    DescriptionField,
    UpdatedAtField,
    CreatedAtField,
    ModifierCharField,
    CreatorCharField,
    StatusField,
)


class IsNull(Func):
    template = '%(expressions)s IS NULL'
    output_field = fields.BooleanField()
    arity = 1


class NotNull(Func):
    template = '%(expressions)s IS NOT NULL'
    output_field = fields.BooleanField()
    arity = 1


class VirtualForeignKey(models.ForeignKey):
    """
    Virtual foreignkey which won't create concret relationship on database level.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("on_delete", models.CASCADE)
        kwargs.setdefault("db_constraint", False)
        super().__init__(*args, **kwargs)


class VirtualManyToMany(models.ManyToManyField):
    """
    Virtual foreignkey which won't create concret relationship on database level.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_constraint", False)
        super().__init__(*args, **kwargs)


class BaseModel(models.Model):
    """
    标准抽象模型模型,可直接继承使用
    """

    description = DescriptionField()  # 描述
    status = models.PositiveSmallIntegerField(choices=CommonStatus.choices, default=CommonStatus.TO_VALID)  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = models.Manager()

    class Meta:
        abstract = True
        verbose_name = '基本模型'
        verbose_name_plural = verbose_name


class UUIDModel(BaseModel):
    """
    标准抽象模型模型,可直接继承使用
    """

    id = AutoUUIDField()
    description = DescriptionField()  # 描述
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True
        verbose_name = 'UUID模型'
        verbose_name_plural = verbose_name


class AuditModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    description = DescriptionField()  # 描述
    status = StatusField()  # 状态
    creator = CreatorCharField()  # 创建者
    modifier = ModifierCharField()  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True
        verbose_name = '审计模型'
        verbose_name_plural = verbose_name


class ToDictModelMixin:  # noqa
    def to_dict(self, fields=None, exclude=None, convert_choice=False, fields_map=None):
        """
        Return a dict containing the data in ``instance`` suitable for passing as
        a Form's ``initial`` keyword argument.

        ``fields`` is an optional list of field names. If provided, return only the
        named.

        ``exclude`` is an optional list of field names. If provided, exclude the
        named from the returned dict, even if they are listed in the ``fields``
        argument.

        ``translate_choice`` If provided, convert the value into display value.

        ``field_map`` is dict object, If provided, perform field name mapping.
        """
        opts = self._meta  # noqa
        fields_map = fields_map or {}
        data = {}
        assert not all([fields, exclude]), "Cannot set both 'fields' and 'exclude' options."
        for f in chain(opts.concrete_fields, opts.private_fields):
            if fields and f.name not in fields:
                continue
            if exclude and f.name in fields:
                continue

            field_name = fields_map.get(f.name, f.name)
            if convert_choice and f.choices:
                data[field_name] = getattr(self, f'get_{f.name}_display')()
            else:
                data[field_name] = f.value_from_object(self)

        for f in opts.many_to_many:
            field_name = fields_map.get(f.name, f.name)
            data[field_name] = [i.id for i in f.value_from_object(self)]
        return data
