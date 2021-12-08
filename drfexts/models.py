from itertools import chain

from django.conf import settings
from django.db import models
from django.db.models import Func, SET_NULL

from .fields import AutoUUIDField, DescriptionField, UpdatedAtField, CreatedAtField, ModifierCharField


class IsNull(Func):
    template = '%(expressions)s IS NULL'
    arity = 1


class NotNull(Func):
    template = '%(expressions)s IS NOT NULL'
    arity = 1


class VirtualForeignKey(models.ForeignKey):
    """
    Virtual foreignkey which won't create concret relationship on database level.
    """

    def __init__(self, *args, **kwargs):
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
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

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


class CoreModel(models.Model):
    """
    核心标准抽象模型模型,可直接继承使用
    增加审计字段, 覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """
    description = DescriptionField()  # 描述
    creator = models.ForeignKey(to=settings.AUTH_USER_MODEL, related_query_name='creator_query', null=True,
                                verbose_name='创建者', on_delete=SET_NULL, db_constraint=False)  # 创建者
    modifier = ModifierCharField()  # 修改者
    dept_belong_id = models.CharField(max_length=64, verbose_name="数据归属部门", null=True, blank=True)
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    class Meta:
        abstract = True
        verbose_name = '核心模型'
        verbose_name_plural = verbose_name


class ToDictModelMixin:
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
        opts = self._meta
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
