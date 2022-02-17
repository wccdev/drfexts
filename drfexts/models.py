from itertools import chain

from django.db import models
from django.db.models import Func, fields
from django.conf import settings
from django.contrib.auth import get_user_model
from .constants import CommonStatus
from .fields import (
    AutoUUIDField,
    UpdatedAtField,
    CreatedAtField,
    StatusField,
    DefaultCodeField,
    AuditStatusField,
    VirtualForeignKey,
)

User = get_user_model()


class IsNull(Func):
    template = '%(expressions)s IS NULL'
    output_field = fields.BooleanField()
    arity = 1


class NotNull(Func):
    template = '%(expressions)s IS NOT NULL'
    output_field = fields.BooleanField()
    arity = 1


class BaseModel(models.Model):
    """
    标准抽象模型模型,可直接继承使用
    """

    status = models.PositiveSmallIntegerField(choices=CommonStatus.choices, default=CommonStatus.TO_VALID)  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = models.Manager()

    class Meta:
        abstract = True
        verbose_name = '基本模型'


class BaseCodeModel(models.Model):
    """
    标准抽象模型模型(增加code),可直接继承使用
    """

    code = DefaultCodeField()  # 编号
    status = models.PositiveSmallIntegerField(choices=CommonStatus.choices, default=CommonStatus.TO_VALID)  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = models.Manager()

    class Meta:
        abstract = True
        verbose_name = '基本模型(code)'


class BaseCreatorModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    status = StatusField()  # 状态
    created_by = VirtualForeignKey("创建人", User, db_column="created_by", related_name='%(class)s_created_by')  # 创建者
    updated_by = VirtualForeignKey("修改人", User, db_column="updated_by", related_name='%(class)s_updated_by')  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True


class UUIDModel(BaseModel):
    """
    标准抽象模型模型,可直接继承使用
    """

    id = AutoUUIDField()
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True
        verbose_name = 'UUID模型'


class AuditModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    status = StatusField()  # 状态
    audit_status = AuditStatusField()  # 审核状态
    created_by = VirtualForeignKey("创建人", User, db_column="created_by", related_name='%(class)s_created_by')  # 创建者
    updated_by = VirtualForeignKey("修改人", User, db_column="updated_by", related_name='%(class)s_updated_by')  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True
        verbose_name = '审核模型'


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
