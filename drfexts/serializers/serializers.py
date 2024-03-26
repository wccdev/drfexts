from django.conf import settings
from django.db.models import CharField
from django.utils.module_loading import import_string
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import ModelSerializer

from drfexts.serializers.fields import NullToEmptyCharField

from ..utils import get_split_query_params

# Get custom fields
SERIALIZER_RELATED_FIELD = import_string(
    getattr(
        settings,
        "DRFEXTS_SERIALIZER_RELATED_FIELD",
        "rest_framework.serializers.PrimaryKeyRelatedField",
    )
)
SERIALIZER_CHOICE_FIELD = import_string(
    getattr(
        settings,
        "DRFEXTS_SERIALIZER_CHOICE_FIELD",
        "rest_framework.serializers.ChoiceField",
    )
)
SERIALIZER_RELATED_TO_FIELD = import_string(
    getattr(
        settings,
        "DRFEXTS_SERIALIZER_RELATED_TO_FIELD",
        "rest_framework.serializers.SlugRelatedField",
    )
)


class WCCModelSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    serializer_choice_field = SERIALIZER_CHOICE_FIELD
    serializer_related_field = SERIALIZER_RELATED_FIELD
    serializer_related_to_field = SERIALIZER_RELATED_TO_FIELD

    serializer_field_mapping = ModelSerializer.serializer_field_mapping.copy()
    serializer_field_mapping[CharField] = NullToEmptyCharField

    # _SELECT_RELATED_FIELDS = []
    # _PREFETCH_RELATED_FIELDS = []
    # _ANNOTATE_FIELDS = {}

    def __init__(self, *args, **kwargs):
        self.ref_name = kwargs.pop("ref_name", None)  # only change to original version!

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    @classmethod
    def process_queryset(cls, request, queryset):
        if hasattr(cls, "_SELECT_RELATED_FIELDS"):
            allow_fields = get_split_query_params(request.query_params, "fields")
            omit_fields = get_split_query_params(request.query_params, "omit")
            related_fields = cls._SELECT_RELATED_FIELDS
            if allow_fields:
                related_fields = [
                    field_name
                    for field_name in cls._SELECT_RELATED_FIELDS
                    if field_name in allow_fields
                ]
            if omit_fields:
                related_fields = [
                    field_name
                    for field_name in cls._SELECT_RELATED_FIELDS
                    if field_name not in omit_fields
                ]
            queryset = queryset.select_related(*related_fields)

        if hasattr(cls, "_PREFETCH_RELATED_FIELDS"):
            allow_fields = get_split_query_params(request.query_params, "fields")
            omit_fields = get_split_query_params(request.query_params, "omit")
            prefetch_fields = cls._PREFETCH_RELATED_FIELDS
            if allow_fields:
                prefetch_fields = [
                    field_name
                    for field_name in cls._PREFETCH_RELATED_FIELDS
                    if field_name in allow_fields
                ]
            if omit_fields:
                prefetch_fields = [
                    field_name
                    for field_name in cls._PREFETCH_RELATED_FIELDS
                    if field_name not in omit_fields
                ]
            queryset = queryset.prefetch_related(*prefetch_fields)

        if hasattr(cls, "_ANNOTATE_FIELDS"):
            allow_fields = get_split_query_params(request.query_params, "fields")
            omit_fields = get_split_query_params(request.query_params, "omit")
            annotate_fields = cls._ANNOTATE_FIELDS
            if allow_fields:
                annotate_fields = {
                    field_name: value
                    for field_name, value in cls._ANNOTATE_FIELDS.items()
                    if field_name in allow_fields
                }
            if omit_fields:
                annotate_fields = {
                    field_name: value
                    for field_name, value in cls._ANNOTATE_FIELDS.items()
                    if field_name not in omit_fields
                }
            queryset = queryset.annotate(**annotate_fields)

        return queryset
