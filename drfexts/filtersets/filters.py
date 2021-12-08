from django import forms
from django.core.exceptions import ImproperlyConfigured
from django_filters.constants import EMPTY_VALUES
from django_filters.fields import RangeField
from rest_framework.filters import OrderingFilter, BaseFilterBackend
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django_filters.filters import (
    CharFilter,
    MultipleChoiceFilter,
    Filter,
    ModelMultipleChoiceFilter, RangeFilter,
)

import operator
from functools import reduce
from django.core.exceptions import ImproperlyConfigured

from .fields import MultipleValueField
from ..widgets import CustomSelectMultiple, CustomRangeWidget


class DjangoFilterBackendListFix(DjangoFilterBackend):
    """
    Fix query params like: /endpoint?a[]=1&a[]=2 to /endpoint?a=1&a=2
    """

    def filter_queryset(self, request, queryset, view):
        fixed_qp = request.query_params.copy()
        for qp in request.query_params:
            if qp.endswith('[]'):
                fixed_qp.setlist(qp[:-2], fixed_qp.pop(qp))

        request._request.GET = fixed_qp
        return super().filter_queryset(request, queryset, view)


class OrderingFieldNameExtFilter(OrderingFilter):
    """
    Extra supporting for ordering by serializer field name
    """

    def get_serializer_class(self, view):
        # If `ordering_fields` is not specified, then we determine a default
        # based on the serializer class, if one exists on the view.
        if hasattr(view, "get_serializer_class"):
            try:
                serializer_class = view.get_serializer_class()
            except AssertionError:
                # Raised by the default implementation if
                # no serializer_class was found
                serializer_class = None
        else:
            serializer_class = getattr(view, "serializer_class", None)

        if serializer_class is None:
            msg = (
                "Cannot use %s on a view which does not have either a "
                "'serializer_class', an overriding 'get_serializer_class' "
                "or 'ordering_fields' attribute."
            )
            raise ImproperlyConfigured(msg % self.__class__.__name__)

        return serializer_class

    def get_ordering(self, request, queryset, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [param.strip() for param in params.split(",")]
            fields = self.get_fixed_fields(fields, view, request)
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def get_default_valid_fields(self, queryset, view, context={}):
        serializer_class = self.get_serializer_class(view)
        return [
            (field.source.replace(".", "__") or field_name, field.label)
            for field_name, field in serializer_class(context=context).fields.items()
            if not getattr(field, "write_only", False) and not field.source == "*"
        ]

    def get_fixed_fields(self, fields, view, request):
        """
        Get query name by field name
        """
        serializer_class = self.get_serializer_class(view)
        default_fields = serializer_class(context={"request": request}).fields
        fixed_fields = []
        for field_name in fields:
            prefix = "-" if field_name.startswith("-") else ""
            field_name = field_name.lstrip("-")
            field = default_fields.get(field_name)
            if field and not getattr(field, "write_only", False) and not field.source == "*":
                fixed_name = field.source.replace(".", "__")
                fixed_fields.append(prefix + (fixed_name or field_name))
            else:
                fixed_fields.append(prefix + field_name)

        return fixed_fields


class SearchFilter(CharFilter):
    """
    This filter performs OR(by default) query on the multi fields.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "icontains")
        self.search_fields = kwargs.pop('search_fields', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()

        if self.search_fields:
            queries = (Q(**{'%s__%s' % (search_field, self.lookup_expr): value}) for search_field in self.search_fields)
            conditions = reduce(operator.or_, queries)
            qs = qs.filter(conditions)
        else:
            lookup = '%s__%s' % (self.field_name, self.lookup_expr)
            qs = self.filter(**{lookup: value})

        return qs


class MultipleValueFilter(Filter):
    """
    支持传入多个值查询一个字段
    使用示例：stage_name = MultipleValueFilter(field_class=CharField, field_name="stage__name", lookup_expr="icontains")
    支持传参方式：
        1. ?stage_name[]=123&stage_name[]=124
        2. ?stage_name=123&stage_name=125
    参考：https://stackoverflow.com/questions/50799411/django-filters-multiple-ids-in-a-single-query-string
    """

    field_class = MultipleValueField

    def __init__(self, *args, field_class, **kwargs):
        kwargs.setdefault('lookup_expr', 'exact')
        super().__init__(*args, field_class=field_class, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        _ = Q()
        lookup = '%s__%s' % (self.field_name, self.lookup_expr)
        for _value in value:
            _ |= Q(**{lookup: _value})
        qs = self.get_method(qs)(_)
        return qs


class DataPermissionFilter(BaseFilterBackend):
    """数据权限filter"""

    @staticmethod
    def data_permission(user, queryset, permission_cls):
        """
        数据权限
        """
        if user.is_anonymous:
            return queryset.none()

        dp = permission_cls(user, queryset)
        queryset = dp.filter()
        return queryset

    def filter_queryset(self, request, queryset, view):
        user = request.user
        queryset = self.data_permission(user, queryset)
        return queryset


class MultiSearchMixin:
    distinct = True
    lookup_expr = "icontains"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", getattr(self, "lookup_expr", "icontains"))
        self.search_fields = kwargs.pop('search_fields', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES or not value:
            return qs

        if self.distinct:
            qs = qs.distinct()

        if self.search_fields:
            queries = (Q(**{'%s__%s' % (search_field, self.lookup_expr): value}) for search_field in self.search_fields)
            conditions = reduce(operator.or_, queries)
            qs = qs.filter(conditions)
        else:
            lookup = '%s__%s' % (self.field_name, self.lookup_expr)
            qs = self.filter(**{lookup: value})

        return qs


class MultiSearchFilter(MultiSearchMixin, CharFilter):
    """
    This filter performs OR(by default) query on the multi fields.
    """

    ...


class MultipleChoiceSearchFilter(MultiSearchMixin, ModelMultipleChoiceFilter):
    """
    Extended MultipleChoiceSearchFilter
    """

    lookup_expr = 'in'


class NotDistinctMultipleChoiceFilter(MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        self.choices = kwargs.get("choices")
        if not self.choices:
            raise ValueError('"choices" is a necessary parameter in this Filter')
        kwargs.setdefault("distinct", False)
        super(NotDistinctMultipleChoiceFilter, self).__init__(*args, **kwargs)

    def is_noop(self, qs, value):
        """
        穷举choice选项时，返回true，避免非必要的查询
        """
        if len(set(value)) == len(self.choices):
            return True
        return False


class IsNullFilter(Filter):
    field_class = forms.NullBooleanField

    def __init__(self, *args, **kwargs):
        kwargs['lookup_expr'] = 'isnull'
        super().__init__(*args, **kwargs)


class IsNotNullFilter(IsNullFilter):

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        return super().filter(qs, not value)


class MultipleSelectFilter(Filter):
    def __init__(self, field_name=None, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        kwargs.setdefault("widget", CustomSelectMultiple)
        super().__init__(field_name=field_name, **kwargs)


class CustomModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", CustomSelectMultiple)
        super().__init__(*args, **kwargs)


class CustomMultipleChoiceFilter(MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", CustomSelectMultiple)
        super().__init__(*args, **kwargs)


class CustomRangeFilter(Filter):
    field_class = RangeField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", CustomRangeWidget)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            if value.start is not None and value.stop is not None:
                if value.start == value.stop:
                    self.lookup_expr = 'exact'
                    value = value.start
                else:
                    self.lookup_expr = 'range'
                    value = (value.start, value.stop)
            elif value.start is not None:
                self.lookup_expr = 'gte'
                value = value.start
            elif value.stop is not None:
                self.lookup_expr = 'lte'
                value = value.stop

        return super().filter(qs, value)

