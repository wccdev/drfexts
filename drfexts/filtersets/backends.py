import warnings

from django.core.exceptions import ImproperlyConfigured
from django_filters.rest_framework import DjangoFilterBackend

from django_filters.filters import (
    BooleanFilter,
    CharFilter,
    NumberFilter,
    TimeFilter,
    UUIDFilter,
    DateFromToRangeFilter,
)
from django_filters.utils import get_model_field
from rest_framework import serializers
from rest_framework.utils.field_mapping import ClassLookupDict

from .filters import IsNullFilter, IsNotNullFilter, CustomModelMultipleChoiceFilter, \
    CustomMultipleChoiceFilter, CustomRangeFilter, MultipleSelectFilter
from ..serializers.fields import IsNotNullField, IsNullField
from ..utils import strtobool
from ..widgets import RangeListWidget

BOOLEAN_CHOICES = (
    ('false', 'False'),
    ('true', 'True'),
)

FILTER_FOR_SERIALIZER_FIELD_DEFAULTS = ClassLookupDict(
    {
        serializers.IntegerField: {'filter_class': CustomRangeFilter},
        serializers.DateField: {'filter_class': DateFromToRangeFilter, 'extra': lambda f: {"widget": RangeListWidget}},
        serializers.DateTimeField: {'filter_class': DateFromToRangeFilter, 'extra': lambda f: {"widget": RangeListWidget}},
        serializers.TimeField: {'filter_class': TimeFilter},
        serializers.DecimalField: {'filter_class': CustomRangeFilter},
        serializers.FloatField: {'filter_class': CustomRangeFilter},
        serializers.BooleanField: {'filter_class': BooleanFilter},
        serializers.NullBooleanField: {'filter_class': BooleanFilter},
        serializers.SlugField: {'filter_class': CharFilter},
        serializers.EmailField: {'filter_class': CharFilter},
        serializers.FileField: {'filter_class': CharFilter},
        serializers.URLField: {'filter_class': CharFilter},
        serializers.UUIDField: {'filter_class': UUIDFilter},
        serializers.ManyRelatedField: {'filter_class': MultipleSelectFilter, 'extra': lambda f: {"distinct": True}},
        serializers.RelatedField: {'filter_class': MultipleSelectFilter},
        serializers.CharField: {'filter_class': CharFilter, 'extra': lambda f: {"lookup_expr": "icontains"}},
        serializers.ReadOnlyField: {'filter_class': CharFilter},
        serializers.JSONField: {'filter_class': CharFilter, 'extra': lambda f: {"lookup_expr": "icontains"}},
        serializers.ListField: {'filter_class': CharFilter, 'extra': lambda f: {"lookup_expr": "contains"}},
        IsNotNullField: {'filter_class': IsNotNullFilter},
        IsNullField: {'filter_class': IsNullFilter},
        serializers.ChoiceField: {
            'filter_class': CustomMultipleChoiceFilter,
            'extra': lambda f: {"choices": list(f.choices.items())},
        },
        serializers.MultipleChoiceField: {
            'filter_class': CustomMultipleChoiceFilter,
            'extra': lambda f: {"choices": list(f.choices.items())},
        },

    }
)


class DjangoFilterBackendListFixMixin:
    """
    A custom filter that supports dynamic table.
    """

    def filter_queryset(self, request, queryset, view):
        fixed_qp = request.query_params.copy()
        for qp in request.query_params:
            if qp.endswith('[]'):
                fixed_qp.setlist(qp[:-2], fixed_qp.pop(qp))

        request._request.GET = fixed_qp
        return super().filter_queryset(request, queryset, view)


class AutoFilterBackendMixin:
    """
    Generate filterset class for
    """

    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        filterset_class = getattr(view, 'filterset_class', None)
        filterset_overwrite = getattr(view, 'filterset_overwrite', {})

        if filterset_class:
            filterset_model = filterset_class._meta.model

            # FilterSets do not need to specify a Meta class
            if filterset_model and queryset is not None:
                assert issubclass(
                    queryset.model, filterset_model
                ), 'FilterSet model %s does not match queryset model %s' % (filterset_model, queryset.model)

            return filterset_class

        serializer = view.get_serializer()

        if not isinstance(serializer, serializers.ModelSerializer):
            return None

        filterset_model = serializer.Meta.model
        filterset_fields = {}

        for filter_name, field in serializer.fields.items():
            if (
                getattr(field, "write_only", False)
                or field.source == "*"
                or isinstance(field, serializers.BaseSerializer)
            ):
                continue

            field_name = field.source.replace(".", "__") or filter_name
            if get_model_field(filterset_model, field_name) is None and filter_name not in queryset.query.annotations:
                continue

            extra = FILTER_FOR_SERIALIZER_FIELD_DEFAULTS[field].get("extra")

            kwargs = {"field_name": field_name}
            if callable(extra):
                kwargs.update(extra(field))

            if "queryset" in kwargs and kwargs["queryset"] is None:
                warnings.warn(f"{filter_name} 字段未提供queryset, 跳过自动成filter!")
                continue

            filterset_field = FILTER_FOR_SERIALIZER_FIELD_DEFAULTS[field]["filter_class"](**kwargs)
            filterset_fields[filter_name] = filterset_field

        if filterset_overwrite:
            filterset_fields.update(filterset_overwrite)

        AutoFilterSet = type("AutoFilterSet", (self.filterset_base,), filterset_fields)

        return AutoFilterSet


class OrderingByFieldNameFilterMixin:
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


class DynamicFilterBackend(
    DjangoFilterBackendListFixMixin, AutoFilterBackendMixin, DjangoFilterBackend
):
    ...
