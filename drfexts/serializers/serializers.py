from rest_flex_fields.serializers import FlexFieldsSerializerMixin
from rest_framework.serializers import ModelSerializer

from .fields import ComplexPKRelatedField


class WCCModelSerializer(FlexFieldsSerializerMixin, ModelSerializer):
    serializer_related_field = ComplexPKRelatedField
