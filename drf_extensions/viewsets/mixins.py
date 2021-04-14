from django.db.models import QuerySet
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.fields import HiddenField, ReadOnlyField
from django.core.exceptions import ImproperlyConfigured


class EagerLoadingMixin:
    function_name = "setup_eager_loading"

    def get_queryset(self, *args, **kwargs):
        """
        Call setup_eager_loading function on serializer
        """
        queryset = super().get_queryset(*args, **kwargs)
        serilaizer_class = self.get_serializer_class()
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
        serilaizer_class = self.get_serializer_class()

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


