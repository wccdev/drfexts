from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Func, fields

from .constants import CommonStatus
from .fields import (
    AuditStatusField,
    AutoUUIDField,
    CreatedAtField,
    CreatedByField,
    DefaultCodeField,
    SimpleStatusField,
    StatusField,
    UpdatedAtField,
    UpdatedByField,
)

__all__ = [
    "IsNull",
    "NotNull",
    "StatusQuerySet",
    "BaseModel",
    "BaseCodeModel",
    "BaseCreatorModel",
    "AuditModel",
    "UUIDModel",
    "serialize_model",
    "serialize_queryset",
]

User = get_user_model()


class IsNull(Func):
    template = "%(expressions)s IS NULL"
    output_field = fields.BooleanField()
    arity = 1


class NotNull(Func):
    template = "%(expressions)s IS NOT NULL"
    output_field = fields.BooleanField()
    arity = 1


class StatusQuerySet(models.QuerySet):
    def editable(self):
        return self.exclude(status__in=[CommonStatus.DELETED, CommonStatus.INVALID])

    def active(self):
        return self.filter(
            status__in=[CommonStatus.VALID, CommonStatus.PAUSED, CommonStatus.TO_INVALID]
        )

    def valid(self):
        return self.filter(status=CommonStatus.VALID)


class BaseModel(models.Model):
    """
    标准抽象模型模型,可直接继承使用
    """

    status = StatusField()  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = "基本模型"


class BaseCodeModel(models.Model):
    """
    标准抽象模型模型(增加code),可直接继承使用
    """

    code = DefaultCodeField()  # 编号
    status = StatusField()  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = "基本模型(code)"


class BaseCreatorModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    status = StatusField()  # 状态
    created_by = CreatedByField()  # 创建者
    updated_by = UpdatedByField()  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True


class SimpleBaseModel(models.Model):
    """
    标准抽象模型模型,可直接继承使用
    """

    status = SimpleStatusField()  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = "基本模型"


class SimpleBaseCodeModel(models.Model):
    """
    标准抽象模型模型(增加code),可直接继承使用
    """

    code = DefaultCodeField()  # 编号
    status = SimpleStatusField()  # 状态
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = "基本模型(code)"


class SimpleBaseCreatorModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    status = SimpleStatusField()  # 状态
    created_by = CreatedByField()  # 创建者
    updated_by = UpdatedByField()  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

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
        verbose_name = "UUID模型"


class AuditModel(models.Model):
    """
    审计抽象模型模型,可直接继承使用
    覆盖字段时, 字段名称请勿修改, 必须统一审计字段名称
    """

    status = StatusField()  # 状态
    audit_status = AuditStatusField()  # 审核状态
    created_by = CreatedByField()  # 创建者
    updated_by = UpdatedByField()  # 修改者
    updated_at = UpdatedAtField()  # 修改时间
    created_at = CreatedAtField()  # 创建时间

    objects = StatusQuerySet.as_manager()

    class Meta:
        abstract = True
        verbose_name = "审核模型"


def serialize_model(model: models.Model) -> Dict[str, Any]:
    """
    模型序列化，会根据 select_related 和 prefetch_related 关联查询的结果进行序列化，
    可以在查询时使用 only、defer 来筛选序列化的字段。
    它不会自做主张的去查询数据库，只用你查询出来的结果，成功避免了 N+1 查询问题。

    """
    serialized = set()

    def _serialize_model(model_: models.Model) -> Dict[str, Any]:

        # 当 model 存在一对一字段时，会陷入循环，使用闭包的自由变量存储已序列化的 model，
        # 在第二次循环到该 model 时直接返回 model.pk，不再循环。
        nonlocal serialized
        if model_ in serialized:
            return model_.pk
        else:
            serialized.add(model_)

        # 当 model 存在一对一或一对多字段，且该字段的值为 None 时，直接返回空{}，否则会报错。
        if model_ is None:
            return {}

        result = {
            name: _serialize_model(foreign_key)
            for name, foreign_key in model_.__dict__["_state"]
            .__dict__.get("fields_cache", {})
            .items()
        }
        buried_fields = getattr(model_, "buried_fields", [])

        for name, value in model_.__dict__.items():
            if name in buried_fields:
                # 不可暴露的字段
                continue
            try:
                model_._meta.get_field(name)  # noqa
            except FieldDoesNotExist:
                # 非模型字段
                continue
            else:
                result[name] = value

        for name, queryset in model_.__dict__.get(
            "_prefetched_objects_cache", {}
        ).items():
            result[name] = serialize_queryset(queryset)

        return result

    return _serialize_model(model)


def serialize_queryset(queryset: models.QuerySet) -> List[Dict[str, Any]]:
    return [serialize_model(model) for model in queryset]
