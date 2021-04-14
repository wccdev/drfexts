from django.core.exceptions import ImproperlyConfigured
from django_filters.constants import EMPTY_VALUES
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .. import compat, utils
from django.db.models import Q
from rest_framework import serializers
from django_filters.filters import (
    BooleanFilter,
    CharFilter,
    ChoiceFilter,
    MultipleChoiceFilter,
    DateFilter,
    DateTimeFilter,
    DateFromToRangeFilter,
    Filter,
    TypedMultipleChoiceFilter,
    NumberFilter,
    TimeFilter,
    UUIDFilter,
)

import operator
from functools import reduce
from django.core.exceptions import ImproperlyConfigured
from distutils.util import strtobool


BOOLEAN_CHOICES = (
    ('false', 'False'),
    ('true', 'True'),
)

FILTER_FOR_SERIALIZER_FIELD_DEFAULTS = {
    serializers.IntegerField: {'filter_class': NumberFilter},
    serializers.DateField: {'filter_class': DateFilter},
    serializers.DateTimeField: {'filter_class': DateTimeFilter},
    serializers.TimeField: {'filter_class': TimeFilter},
    serializers.DecimalField: {'filter_class': NumberFilter},
    serializers.FloatField: {'filter_class': NumberFilter},
    serializers.SlugField: {'filter_class': CharFilter},
    serializers.EmailField: {'filter_class': CharFilter},
    serializers.FileField: {'filter_class': CharFilter},
    serializers.URLField: {'filter_class': CharFilter},
    serializers.UUIDField: {'filter_class': UUIDFilter},
    serializers.PrimaryKeyRelatedField: {'filter_class': NumberFilter},
    serializers.CharField: {'filter_class': CharFilter, 'extra': lambda f: {"lookup_expr": "icontains"}},
    serializers.ChoiceField: {
        'filter_class': ChoiceFilter,
        'extra': lambda f: {"choices": f.choices, "always_filter": False},
    },
    serializers.MultipleChoiceField: {
        'filter_class': MultipleChoiceFilter,
        'extra': lambda f: {"choices": f.choices, "always_filter": False},
    },
    serializers.BooleanField: {
        'filter_class': TypedMultipleChoiceFilter,
        'extra': lambda f: {"coerce": strtobool, "choices": BOOLEAN_CHOICES, "always_filter": False},
    },
    serializers.NullBooleanField: {
        'filter_class': TypedMultipleChoiceFilter,
        'extra': lambda f: {"coerce": strtobool, "choices": BOOLEAN_CHOICES, "always_filter": False},
    },
}


class DjangoFilterBackendListFix(DjangoFilterBackend):
    """
    Fix query params like: /api/wip/wipdata?a[]=1&a[]=2
    """

    def filter_queryset(self, request, queryset, view):
        fixed_query_params = request.query_params.copy()
        for qp in request.query_params:
            if qp.endswith('[]'):
                fixed_query_params.setlist(qp.rstrip('[]'), fixed_query_params.pop(qp))

        request._request.GET = fixed_query_params
        return super().filter_queryset(request, queryset, view)


class OrderingNameFixFilter(OrderingFilter):
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
