import logging
import operator
from functools import reduce

from django.contrib.postgres.search import SearchQuery
from django.contrib.postgres.search import SearchVector
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Exists
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models.constants import LOOKUP_SEP
from django_filters.filters import BooleanFilter
from django_filters.filters import CharFilter
from django_filters.filters import Filter
from django_filters.filters import TimeFilter
from django_filters.filters import UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import filterset
from django_filters.utils import get_model_field
from rest_framework import serializers
from rest_framework.filters import OrderingFilter
from rest_framework.filters import SearchFilter as DefaultSearchFilter
from rest_framework.utils.field_mapping import ClassLookupDict

from ..serializers.fields import ComplexPKRelatedField
from ..serializers.fields import DisplayChoiceField
from ..serializers.fields import IsNotNullField
from ..serializers.fields import IsNullField
from .filters import ArrayMultipleChoiceFilter
from .filters import ExtendedCharFilter
from .filters import ExtendedDateFromToRangeFilter
from .filters import ExtendedDisplayMultipleChoiceFilter
from .filters import ExtendedModelMultipleChoiceFilter
from .filters import ExtendedMultipleChoiceFilter
from .filters import ExtendedNumberFilter
from .filters import IsNotNullFilter
from .filters import IsNullFilter
from .filters import MultipleSelectFilter

logger = logging.getLogger(__name__)


BOOLEAN_CHOICES = (
    ("false", "False"),
    ("true", "True"),
)

FILTER_FOR_SERIALIZER_FIELD_DEFAULTS = ClassLookupDict(
    {
        serializers.IntegerField: {"filter_class": ExtendedNumberFilter},
        serializers.DateField: {"filter_class": ExtendedDateFromToRangeFilter},
        serializers.DateTimeField: {"filter_class": ExtendedDateFromToRangeFilter},
        serializers.TimeField: {"filter_class": TimeFilter},
        serializers.DecimalField: {"filter_class": ExtendedNumberFilter},
        serializers.FloatField: {"filter_class": ExtendedNumberFilter},
        serializers.BooleanField: {"filter_class": BooleanFilter},
        serializers.EmailField: {"filter_class": CharFilter},
        serializers.FileField: {"filter_class": CharFilter},
        serializers.URLField: {"filter_class": CharFilter},
        serializers.UUIDField: {"filter_class": UUIDFilter},
        serializers.PrimaryKeyRelatedField: {
            "filter_class": ExtendedModelMultipleChoiceFilter,
            "extra": lambda f: {"queryset": f.queryset, "distinct": False},
        },
        serializers.SlugRelatedField: {
            "filter_class": ExtendedModelMultipleChoiceFilter,
            "extra": lambda f: {
                "queryset": f.queryset,
                "to_field_name": f.slug_field,
                "distinct": False,
            },
        },
        serializers.ManyRelatedField: {
            "filter_class": ExtendedModelMultipleChoiceFilter,
            "extra": lambda f: {
                "queryset": f.child_relation.queryset,
                "distinct": True,
            },
        },
        serializers.RelatedField: {"filter_class": MultipleSelectFilter},
        serializers.JSONField: {
            "filter_class": CharFilter,
            "extra": lambda f: {"lookup_expr": "contains"},
        },
        serializers.ListField: {
            "filter_class": MultipleSelectFilter,
            "extra": lambda f: {"lookup_expr": "overlap"},
        },
        IsNotNullField: {"filter_class": IsNotNullFilter},
        IsNullField: {"filter_class": IsNullFilter},
        serializers.ReadOnlyField: {"filter_class": CharFilter},
        DisplayChoiceField: {
            "filter_class": ExtendedDisplayMultipleChoiceFilter,
            "extra": lambda f: {"choices": list(f.choices.items()), "distinct": False},
        },
        serializers.ChoiceField: {
            "filter_class": ExtendedMultipleChoiceFilter,
            "extra": lambda f: {"choices": list(f.choices.items()), "distinct": False},
        },
        serializers.CharField: {"filter_class": ExtendedCharFilter},
    }
)


class InitialFilterSet(filterset.FilterSet):
    def __init__(self, data=None, *args, **kwargs):
        # if filterset is bound, use initial values as defaults
        if data is not None:
            # get a mutable copy of the QueryDict
            data = data.copy()

            for name, f in self.base_filters.items():
                initial = f.extra.get("initial")

                # filter param is either missing or empty, use initial as default
                if not data.get(name) and initial:
                    data[name] = initial

        super().__init__(data, *args, **kwargs)


class AutoFilterBackend(DjangoFilterBackend):
    """
    Generate filterset class for
    """

    filterset_base = InitialFilterSet

    def filter_queryset(self, request, queryset, view):
        fixed_query_params = request.query_params.copy()
        for qp in request.query_params:
            if qp.endswith("[]"):
                fixed_query_params.setlist(qp.rstrip("[]"), fixed_query_params.pop(qp))

        request._request.GET = fixed_query_params
        return super().filter_queryset(request, queryset, view)

    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        filterset_class = getattr(view, "filterset_class", None)
        filterset_fields_overwrite = {}
        if hasattr(view, "get_filterset_fields_overwrite"):
            filterset_fields_overwrite = view.get_filterset_fields_overwrite()

        if filterset_class:
            filterset_model = filterset_class._meta.model  # noqa

            # FilterSets do not need to specify a Meta class
            if filterset_model and queryset is not None:
                assert issubclass(queryset.model, filterset_model), (
                    f"FilterSet model {filterset_model} does not match queryset model {queryset.model}"  # noqa
                )

            return filterset_class

        serializer = view.get_serializer()

        if not isinstance(serializer, serializers.ModelSerializer):
            return None

        filterset_model = serializer.Meta.model  # noqa
        filterset_fields = {}

        overwrite_fields = {
            k: v for k, v in filterset_fields_overwrite.items() if isinstance(v, Filter)
        }
        overwrite_kwargs = {
            k: v for k, v in filterset_fields_overwrite.items() if isinstance(v, dict)
        }

        def filters_from_serializer(
            _serializer, field_name_prefix="", filter_name_prefix="", filter_kwargs=None
        ):
            filter_kwargs = filter_kwargs or {}
            if isinstance(_serializer, serializers.ListSerializer):
                _serializer = _serializer.child

            if not hasattr(_serializer, "fields"):
                return

            for filter_name, field in _serializer.fields.items():
                if getattr(field, "write_only", False) or field.source == "*":
                    continue

                field_name = field.source.replace(".", "__") or filter_name
                if field_name_prefix:
                    field_name = field_name_prefix + "__" + field_name

                if filter_name_prefix:
                    filter_name = filter_name_prefix + "." + filter_name

                if get_model_field(filterset_model, field_name) is None and (
                    queryset is not None
                    and filter_name not in queryset.query.annotations
                ):
                    continue

                if isinstance(
                    field,
                    (
                        serializers.BaseSerializer,
                        serializers.ManyRelatedField,
                        ComplexPKRelatedField,
                    ),
                ):
                    child_field = field
                    if isinstance(field, serializers.ManyRelatedField):
                        child_field = field.child_relation
                        filter_kwargs = {"distinct": True}

                    filters_from_serializer(
                        child_field,
                        field_name_prefix=field_name,
                        filter_name_prefix=filter_name,
                        filter_kwargs=filter_kwargs,
                    )

                try:
                    filter_spec = FILTER_FOR_SERIALIZER_FIELD_DEFAULTS[field]
                except KeyError:
                    logger.debug(f"{filter_name} 字段未找到过滤器, 跳过自动成filter!")
                    continue

                if isinstance(field, serializers.ListField) and isinstance(
                    field.child, serializers.ChoiceField
                ):
                    filter_spec = {
                        "filter_class": ArrayMultipleChoiceFilter,
                        "extra": lambda f: {
                            "choices": list(f.child.choices.items()),
                            "distinct": False,
                        },
                    }

                extra = filter_spec.get("extra")
                kwargs = {
                    "field_name": field_name,
                    "label": field.label,
                    "help_text": field.help_text,
                }
                if callable(extra):
                    kwargs.update(extra(field))

                kwargs.update(filter_kwargs)
                # Fix when set custom through model for `MantToManyField`
                if (
                    isinstance(field, serializers.PrimaryKeyRelatedField)
                    or isinstance(field, serializers.ManyRelatedField)
                ) and kwargs.get("queryset") is None:
                    related_model_field = field.parent.Meta.model._meta.get_field(
                        field.source
                    )
                    kwargs["queryset"] = (
                        related_model_field.related_model._default_manager
                    )

                if "queryset" in kwargs and kwargs["queryset"] is None:
                    logger.debug(f"{filter_name} 字段未提供queryset, 跳过自动成filter!")
                    continue

                overwrite_value = overwrite_kwargs.get(filter_name)
                if overwrite_value:
                    kwargs.update(overwrite_value)

                filterset_field = filter_spec["filter_class"](**kwargs)
                filterset_fields[filter_name] = filterset_field

        filters_from_serializer(serializer)
        filterset_fields.update(overwrite_fields)

        base_classes = (self.filterset_base,)
        if hasattr(view, "filterset_base_classes"):
            base_classes = view.filterset_base_classes + base_classes

        AutoFilterSet = type("AutoFilterSet", base_classes, filterset_fields)  # noqa
        return AutoFilterSet


class OrderingFilterBackend(OrderingFilter):
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
            fields = [param.strip().split(".")[0] for param in params.split(",")]
            fields = self.get_fixed_fields(fields, view, request)
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def get_default_valid_fields(self, queryset, view, context=None):
        serializer_class = self.get_serializer_class(view)
        return [
            (field.source.replace(".", "__") or field_name, field.label)
            for field_name, field in serializer_class(
                context=context or {}
            ).fields.items()
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
            if (
                field
                and not getattr(field, "write_only", False)
                and not field.source == "*"
            ):
                fixed_name = field.source.replace(".", "__")
                fixed_fields.append(prefix + (fixed_name or field_name))
            else:
                fixed_fields.append(prefix + field_name)

        return fixed_fields


class SearchFilter(DefaultSearchFilter):
    def get_search_terms(self, request):
        """
        Search terms are set by a ?search=... query parameter,
        and may be comma and/or whitespace delimited.
        """
        params = request.query_params.get(self.search_param, "")
        params = params.strip()
        params = params.replace("\x00", "")  # strip null characters
        params = params.replace(",", " ")
        params = params.replace("，", " ")
        return params.split()

    def construct_search(self, field_name):
        lookup = self.lookup_prefixes.get(field_name[0])
        if lookup:
            field_name = field_name[1:]
        else:
            lookup = "contains"
        return LOOKUP_SEP.join([field_name, lookup])

    def get_choice_fields_mapping(self, queryset, search_fields):
        choice_fields_mapping = {}
        for search_field in search_fields:
            field = get_model_field(queryset.model, search_field)
            lookup = "in"
            if not field:
                continue
            if hasattr(field, "base_field"):
                field = field.base_field
                lookup = "overlap"

            if choices := getattr(field, "choices", None):
                if hasattr(choices, "choices"):
                    choices = choices.choices
                choice_fields_mapping[search_field] = (field.choices, lookup)
        return choice_fields_mapping

    def get_choice_seach_value(self, search_term, choices):
        value = []
        for v, label in choices:
            if search_term in str(label):
                value.append(v)
        return value

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)

        if not search_fields or not search_terms:
            return queryset

        choice_fields_mapping = self.get_choice_fields_mapping(queryset, search_fields)
        orm_lookups = [
            self.construct_search(str(search_field))
            for search_field in search_fields
            if search_field not in choice_fields_mapping
        ]

        base = queryset
        conditions = []
        for search_term in search_terms:
            queries = [Q(**{orm_lookup: search_term}) for orm_lookup in orm_lookups]

            queries.extend(
                [
                    Q(
                        **{
                            f"{field}__{lookup}": self.get_choice_seach_value(
                                search_term, choices
                            )
                        }
                    )
                    for field, (choices, lookup) in choice_fields_mapping.items()
                ]
            )
            conditions.append(reduce(operator.or_, queries))
        queryset = queryset.filter(reduce(operator.and_, conditions))

        if self.must_call_distinct(queryset, search_fields):
            # inspired by django.contrib.admin
            # this is more accurate than .distinct form M2M relationship
            # also is cross-database
            queryset = queryset.filter(pk=OuterRef("pk"))
            queryset = base.filter(Exists(queryset))
        return queryset


class FullTextSearchFilter(DefaultSearchFilter):
    """
    Search filter that supports fulltext search
    """

    search_vector = None
    search_query = None

    def get_search_vector(self):
        if isinstance(self.search_vector, (list, tuple)):
            return SearchVector(*self.search_vector)
        elif isinstance(self.search_vector, SearchVector):
            return self.search_vector
        elif self.search_vector is None:
            return

        raise ImproperlyConfigured(
            "`search_vector` must be type of list, tuple or 'SearchVector' instance."
        )

    def get_search_query(self, search_terms):
        if self.search_query is None:
            return SearchQuery(" ".join(search_terms))
        elif isinstance(self.search_query, SearchQuery):
            return self.search_query

        raise ImproperlyConfigured("`search_query` must be instance of 'SearchQuery'")

    def filter_queryset(self, request, queryset, view):
        search_terms = self.get_search_terms(request)
        if not search_terms:
            return queryset

        search_vector = self.get_search_vector()
        search_query = self.get_search_query(search_terms)

        if not search_vector or not search_query:
            return queryset

        return queryset.annotate(search=search_vector).filter(search=search_query)
