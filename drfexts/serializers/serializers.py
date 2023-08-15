from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import ModelSerializer

from .fields import ComplexPKRelatedField


class WCCModelSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    serializer_related_field = ComplexPKRelatedField

    def __init__(self, *args, **kwargs):
        self.ref_name = kwargs.pop("ref_name", None)  # only change to original version!

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)
