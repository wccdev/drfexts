import operator
from functools import reduce

from django import forms
from django.db.models import Q
from django_filters.constants import EMPTY_VALUES
from django_filters.fields import RangeField
from django_filters.filters import (
    CharFilter,
    DateFromToRangeFilter,
    Filter,
    ModelMultipleChoiceFilter,
    MultipleChoiceFilter,
)
from rest_framework.filters import BaseFilterBackend

from .fields import DisplayMultipleChoiceField, MultipleValueField
from .widgets import (
    ExtendedDateRangeWidget,
    ExtendedRangeWidget,
    FixedQueryArrayWidget,
    LookupTextInput,
)


class SearchFilter(CharFilter):
    """
    This filter performs OR(by default) query on the multi fields.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", "icontains")
        self.search_fields = kwargs.pop("search_fields", None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()

        if self.search_fields:
            queries = (
                Q(**{"%s__%s" % (search_field, self.lookup_expr): value})
                for search_field in self.search_fields
            )
            conditions = reduce(operator.or_, queries)
            qs = qs.filter(conditions)
        else:
            lookup = "%s__%s" % (self.field_name, self.lookup_expr)
            qs = self.filter(**{lookup: value})

        return qs


class MultipleValueFilter(Filter):
    """
    支持传入多个值查询一个字段
    使用示例：stage_name = MultipleValueFilter(field_class=CharField, field_name="stage__name", lookup_expr="icontains")
    支持传参方式：
        1. ?stage_name[]=123&stage_name[]=124
        2. ?stage_name=123&stage_name=125
        3. ?stage_name=123,125
    """

    field_class = MultipleValueField

    def __init__(self, *args, field_class, **kwargs):
        kwargs.setdefault("lookup_expr", "exact")
        kwargs.setdefault("widget", FixedQueryArrayWidget)
        super().__init__(*args, field_class=field_class, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()

        lookup = "%s__%s" % (self.field_name, self.lookup_expr)
        queries = (Q(**{lookup: val}) for val in value)
        conditions = reduce(operator.or_, queries)
        qs = self.get_method(qs)(conditions)
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
    lookup_expr = "icontains"

    def __init__(self, *args, search_fields, **kwargs):
        self.search_fields = search_fields
        kwargs.setdefault("lookup_expr", self.lookup_expr)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if self.distinct:  # noqa
            qs = qs.distinct()

        queries = (
            Q(**{"%s__%s" % (search_field, self.lookup_expr): value})
            for search_field in self.search_fields
        )
        conditions = reduce(operator.or_, queries)
        qs = self.get_method(qs)(conditions)  # noqa
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

    lookup_expr = "in"


class IsNullFilter(Filter):
    field_class = forms.NullBooleanField

    def __init__(self, *args, **kwargs):
        kwargs["lookup_expr"] = "isnull"
        super().__init__(*args, **kwargs)


class IsNotNullFilter(IsNullFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        return super().filter(qs, not value)


class MultipleSelectFilter(Filter):
    def __init__(self, field_name=None, **kwargs):
        kwargs.setdefault("lookup_expr", "in")
        kwargs.setdefault("widget", FixedQueryArrayWidget)
        super().__init__(field_name=field_name, **kwargs)


class ExtendedModelMultipleChoiceFilter(ModelMultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", FixedQueryArrayWidget)
        super().__init__(*args, **kwargs)


class ExtendedMultipleChoiceFilter(MultipleChoiceFilter):
    always_filter = False

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", FixedQueryArrayWidget)
        super().__init__(*args, **kwargs)

    def is_noop(self, qs, value):
        """
        Return `True` to short-circuit unnecessary and potentially slow
        filtering.
        """
        if self.always_filter:
            return False

        # A reasonable default for being a noop...
        if len(value) == len(self.field.choices):
            return True

        return False


class ExtendedDisplayMultipleChoiceFilter(ExtendedMultipleChoiceFilter):
    field_class = DisplayMultipleChoiceField


class ExtendedRangeFilterMixin:
    lookup_expr = None

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        if value.start is not None and value.stop is not None:
            if value.start == value.stop:
                self.lookup_expr = "exact"
                value = value.start
            else:
                self.lookup_expr = "range"
                value = (value.start, value.stop)
        elif value.start is not None:
            self.lookup_expr = "gte"
            value = value.start
        elif value.stop is not None:
            self.lookup_expr = "lte"
            value = value.stop

        return super().filter(qs, value)  # noqa


class ExtendedNumberFilter(ExtendedRangeFilterMixin, Filter):
    field_class = RangeField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", ExtendedRangeWidget)
        super().__init__(*args, **kwargs)


class ExtendedDateFromToRangeFilter(DateFromToRangeFilter):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", ExtendedDateRangeWidget)
        super().__init__(*args, **kwargs)


class ExtendedCharFilter(CharFilter):
    EMPTY_VALUES = EMPTY_VALUES + ("None",)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", LookupTextInput)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        value, lookup_expr = value.split(":")
        if value in self.EMPTY_VALUES:
            return qs

        self.lookup_expr = lookup_expr
        return super().filter(qs, value)
