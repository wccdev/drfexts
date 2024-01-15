from django.conf import settings
from django.utils.module_loading import import_string
from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import ModelSerializer

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

    def __init__(self, *args, **kwargs):
        self.ref_name = kwargs.pop("ref_name", None)  # only change to original version!

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)
