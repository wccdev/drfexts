from django.conf import settings
from django.utils.module_loading import import_string
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import ModelSerializer

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

    # _SELECT_RELATED_FIELDS = []
    # _PREFETCH_RELATED_FIELDS = []

    def __init__(self, *args, **kwargs):
        self.ref_name = kwargs.pop("ref_name", None)  # only change to original version!

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    @classmethod
    def process_queryset(cls, request, queryset):
        if hasattr(cls, "_SELECT_RELATED_FIELDS"):
            if allow_fields := get_split_query_params(request.query_params, "fields"):
                queryset = queryset.select_related(
                    *[
                        field_name
                        for field_name in cls._SELECT_RELATED_FIELDS
                        if field_name in allow_fields
                    ]
                )
            else:
                queryset = queryset.select_related(*cls._SELECT_RELATED_FIELDS)
        if hasattr(cls, "_PREFETCH_RELATED_FIELDS"):
            if omit_fields := get_split_query_params(request.query_params, "omit"):
                queryset = queryset.prefetch_related(
                    *[
                        field_name
                        for field_name in cls._PREFETCH_RELATED_FIELDS
                        if field_name not in omit_fields
                    ]
                )
            else:
                queryset = queryset.prefetch_related(*cls._PREFETCH_RELATED_FIELDS)
        return queryset
