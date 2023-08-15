from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet
from rest_framework.fields import ReadOnlyField
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.viewsets import GenericViewSet

from drfexts.renderers import CustomCSVRenderer, CustomXLSXRenderer

from .serializers.mixins import ExportSerializerMixin


class EagerLoadingMixin:
    function_name = "setup_eager_loading"

    def get_queryset(self, *args, **kwargs):
        """
        Call setup_eager_loading function on serializer
        """
        queryset = super().get_queryset(*args, **kwargs)
        serilaizer_class = self.get_serializer_class()  # noqa
        if hasattr(serilaizer_class, "setup_eager_loading") and callable(
            serilaizer_class.setup_eager_loading
        ):
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
        1. The mixin is intended for performance optimization
        and you don't need it in most cases.
    """

    # If using Django filters in the API, these labels mustn't
    # conflict with any model field names.
    include_only_fields_name = "only_fields"
    expand_only_fields_name = "expand_only_fields"
    exclude_only_fields_name = "exclude_only_fields"

    def get_queryset(self):
        """
        Select only fields
        """
        queryset = super().get_queryset()
        serilaizer_class = self.get_serializer_class()  # noqa

        assert issubclass(serilaizer_class, ModelSerializer), (
            f"Class {serilaizer_class.__class__.__name__} "
            f'must inherit from "ModelSerializer"'
        )

        if getattr(queryset, "_result_cache", None):
            return queryset

        meta = getattr(serilaizer_class, "Meta", None)
        only_fields = getattr(meta, self.include_only_fields_name, None)
        expand_only_fields = set(getattr(meta, self.expand_only_fields_name, []))
        # You may need to set this attribute when fetch attrs in `SerializerMethod`
        # or in a nested serializer
        exclude_query_fields = set(getattr(meta, self.exclude_only_fields_name, []))
        if only_fields and exclude_query_fields:
            raise ImproperlyConfigured(
                "You cannot set both 'only_fields' and 'exclude_only_fields'."
            )

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


class ExtGenericViewSet(GenericViewSet):
    _default_key = "default"
    queryset_function_name = "process_queryset"
    # The filter backend classes to use for queryset filtering

    def get_serializer_class(self):
        """
        支持针对不同action指定不同的序列化器
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

    def get_serializer(self, *args, **kwargs):
        """
        支持动态设置序列化器字段
        """
        serializer_class = self.get_serializer_class()
        if hasattr(serializer_class, "get_included_fields") and callable(
            serializer_class.get_included_fields
        ):
            included_fields = serializer_class.get_included_fields(self, self.request)
            if included_fields:
                kwargs["fields"] = included_fields

        if hasattr(serializer_class, "get_excluded_fields") and callable(
            serializer_class.get_excluded_fields
        ):
            excluded_fields = serializer_class.get_excluded_fields(self, self.request)
            if excluded_fields:
                kwargs["omit"] = excluded_fields

        kwargs.setdefault("context", self.get_serializer_context())
        return serializer_class(*args, **kwargs)

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
            "or override the `get_queryset()` method." % self.__class__.__name__
        )

        queryset = self.queryset
        if isinstance(queryset, QuerySet):
            # Ensure queryset is re-evaluated on each request.
            queryset = queryset.all()
            # Perform optimization on queryset
            serializer_class = self.get_serializer_class()
            if hasattr(serializer_class, self.queryset_function_name):
                queryset = getattr(serializer_class, self.queryset_function_name)(
                    self.request, queryset
                )

        return queryset


class ExportMixin:
    """
    Export data to csv/xlsx file
    """

    export_actions = ["list"]
    default_base_filename = "export"

    def is_export_action(self) -> bool:
        """
        Return True if the current action is an export action.
        :return:
        """
        if not hasattr(self.request, "accepted_media_type"):
            return False

        return self.request.accepted_media_type.startswith(  # noqa
            (
                "text/csv",
                "application/xlsx",
            )
        )

    def get_renderers(self):
        """
        Instantiates and returns the list of renderers that this view can use.
        """
        renderers = super().get_renderers()  # noqa
        if self.action in self.export_actions:  # noqa
            return renderers + [CustomCSVRenderer(), CustomXLSXRenderer()]

        return renderers

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        :return:
        """
        serializer_class = super().get_serializer_class()  # noqa
        if self.is_export_action():

            class ExportSerializer(ExportSerializerMixin, serializer_class):
                ...

            return ExportSerializer

        return serializer_class

    def get_renderer_context(self):
        """
        Return the renderer context to use for rendering.
        :return:
        """
        context = super().get_renderer_context()  # noqa
        export_filename = self.get_export_filename()
        if export_filename:
            context["writer_opts"] = {"filename": export_filename}

        return context

    def get_export_filename(self):
        """
        Return the filename of the export file.
        :return:
        """
        if "filename" in self.request.query_params:  # noqa
            return self.request.query_params["filename"]  # noqa

        return f"{self.default_base_filename}.csv"
