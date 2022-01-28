from django.db.models import QuerySet
from rest_framework.relations import ManyRelatedField, RelatedField
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.fields import ReadOnlyField
from django.core.exceptions import ImproperlyConfigured
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet
from drfexts.metadata import VueTableMetadata
from drfexts.renderers import CustomExcelRenderer, CustomCSVRenderer


class EagerLoadingMixin:
    function_name = "setup_eager_loading"

    def get_queryset(self, *args, **kwargs):
        """
        Call setup_eager_loading function on serializer
        """
        queryset = super().get_queryset(*args, **kwargs)
        serilaizer_class = self.get_serializer_class()  # noqa
        if hasattr(serilaizer_class, "setup_eager_loading") and callable(serilaizer_class.setup_eager_loading):
            queryset = serilaizer_class.setup_eager_loading(queryset)
            assert isinstance(queryset, QuerySet), (
                f"Expected '{self.function_name}' to return a QuerySet, "
                f"but got a {type(queryset).__name__} instead."
            )

        return queryset


class SelectOnlyMixin:
    """
    Mixin used to define select-only fields for queryset
    Cautions:
        1. The mixin is intended for performance optimization and you don't need it in most cases.
    """

    # If using Django filters in the API, these labels mustn't conflict with any model field names.
    include_only_fields_name = "only_fields"
    expand_only_fields_name = "expand_only_fields"
    exclude_only_fields_name = "exclude_only_fields"

    def get_queryset(self):
        """
        Select only fields
        """
        queryset = super().get_queryset()
        serilaizer_class = self.get_serializer_class()  # noqa

        assert issubclass(
            serilaizer_class, ModelSerializer
        ), f'Class {serilaizer_class.__class__.__name__} must inherit from "ModelSerializer"'

        if getattr(queryset, "_result_cache", None):
            return queryset

        meta = getattr(serilaizer_class, "Meta", None)
        only_fields = getattr(meta, self.include_only_fields_name, None)
        expand_only_fields = set(getattr(meta, self.expand_only_fields_name, []))
        # You may need to set this attribute when fetch attrs in `SerializerMethod`
        # or in a nested serializer
        exclude_query_fields = set(getattr(meta, self.exclude_only_fields_name, []))
        if only_fields and exclude_query_fields:
            raise ImproperlyConfigured("You cannot set both 'only_fields' and 'exclude_only_fields'.")

        if only_fields:
            return queryset.only(*only_fields)

        only_fields_name = set()
        for field in serilaizer_class()._readable_fields:
            if field.field_name in exclude_query_fields:
                continue

            # TODO: support nested serializer
            if isinstance(field, (ReadOnlyField, Serializer)):
                continue

            source = getattr(field, "source", None)
            # serliazer method class will set source to '*'
            if source == "*":
                continue

            if source:
                query_name = "__".join(source.split("."))
            else:
                query_name = field.field_name

            only_fields_name.add(query_name)

        only_fields_name |= expand_only_fields
        if only_fields_name:
            queryset = queryset.only(*only_fields_name)

        return queryset


class DynamicListModelMixin:
    """
    Auto creating serializer-based filter.
    """
    metadata_class = VueTableMetadata
    filter_backends = api_settings.DEFAULT_FILTER_BACKENDS

    def options(self, request, *args, **kwargs):
        """
        Handler method for HTTP 'OPTIONS' request.
        """
        metadata_class = getattr(self, "metadata_class", None)
        if metadata_class is None:
            return getattr(self, "http_method_not_allowed")(request, *args, **kwargs)

        data = metadata_class().determine_metadata(request, self)
        return Response(data)


class ExtGenericViewSet(GenericViewSet):
    _default_key = "default"
    # The filter backend classes to use for queryset filtering

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        Defaults to using `self.serializer_class`.

        You may want to override this if you need to provide different
        serializations depending on the incoming request.

        (Eg. admins get full serialization, others get basic serialization)
        """
        assert self.serializer_class is not None, (
                "'%s' should either include a `serializer_class` attribute, "
                "or override the `get_serializer_class()` method." % self.__class__.__name__
        )
        if isinstance(self.serializer_class, dict):  # 多个serializer_class
            assert (
                    self._default_key in self.serializer_class
            ), f"多个serializer时serializer_class必须包含下列key:{self._default_key}"
            if self.serializer_class.get(self.action):
                return self.serializer_class.get(self.action)
            else:
                return self.serializer_class.get(self._default_key)

        return self.serializer_class

    def data_permissions(self, request, view, queryset):
        """
        检查数据权限
        """
        for permission in self.get_permissions():
            if hasattr(permission, "data_permission"):
                return permission.data_permission(request, view, queryset)

    def get_queryset(self):
        """
        Get the list of items for this view.
        This must be an iterable, and may be a queryset.
        Defaults to using `self.queryset`.

        This method should always be used rather than accessing `self.queryset`
        directly, as `self.queryset` gets evaluated only once, and those results
        are cached for all subsequent requests.

        You may want to override this if you need to provide different
        querysets depending on the incoming request.

        (Eg. return a list of items that is specific to the user)
        """
        assert self.queryset is not None, (
                "'%s' should either include a `queryset` attribute, "
                "or override the `get_queryset()` method."
                % self.__class__.__name__
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
            # Perform optimization on queryset
            serilaizer_class = self.get_serializer_class()
            if hasattr(serilaizer_class, "setup_eager_loading"):
                queryset = serilaizer_class.setup_eager_loading(queryset)

        return queryset


class ExportMixin:
    """
    Export data to csv/xlsx file
    """
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES + [CustomCSVRenderer, CustomExcelRenderer]

    def get_export_columns(self):
        """
        获取导出列信息
        :return:
        """
        serializer = self.get_serializer()  # noqa
        fields = serializer._readable_fields
        columns = {}
        for field in fields:
            field_name = field.field_name
            if not field.style.get("column_visible", True):
                continue

            columns[field_name] = {"column_name": str(field.label)}
            if not isinstance(field, (ManyRelatedField, RelatedField)) and getattr(field, "choices", None):
                columns[field_name]["choices"] = dict(field.choices)
        return columns

    def get_renderer_context(self):
        context = super().get_renderer_context()  # noqa
        export_columns = self.get_export_columns()
        context['header'] = (
            self.request.GET['fields'].split(',')  # noqa
            if 'fields' in self.request.GET else export_columns.keys())  # noqa
        context['labels'] = {
            field_name: attrs["column_name"] for field_name, attrs in export_columns.items()
        }
        context['value_mapping'] = {
            field_name: attrs["choices"] for field_name, attrs in export_columns.items() if "choices" in attrs
        }
        return context
