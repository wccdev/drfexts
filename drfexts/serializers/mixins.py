import json
from collections import OrderedDict
from functools import cached_property

from rest_framework.fields import BooleanField, ChoiceField, SkipField
from rest_framework.relations import PKOnlyObject
from rest_framework.serializers import BaseSerializer, ListSerializer, ModelSerializer

from ..utils import get_serializer_field
from .fields import ComplexPKRelatedField


class DynamicFieldsSerializer(ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop("fields", None)

        # Instantiate the superclass normally
        super(DynamicFieldsSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ExportSerializerMixin:
    @cached_property
    def _export_info(self):
        if self.context["request"].query_params.get("fields"):
            fields = self.context["request"].query_params["fields"].split(",")
        else:
            fields = []

        fields_map = json.loads(
            self.context["request"].query_params.get("fields_map", "{}")
        )
        return fields, fields_map

    @property
    def export_fields(self):
        """
        获取导出字段
        :return:
        """
        field_names, fields_map = self._export_info
        if not field_names:
            yield from self._readable_fields
            return

        for field_name in field_names:
            field, source_attrs, is_skipped = get_serializer_field(self, field_name)
            if is_skipped:
                continue

            field.label = fields_map.get(field_name, field.label)
            field.source_attrs = source_attrs
            yield field

    def _trans_value(self, value, field):
        """
        字段进行翻译
        :param value:
        :param field:
        :return:
        """
        if isinstance(field, ComplexPKRelatedField):
            value = value.get("label")
        elif isinstance(getattr(field, "child_relation", None), ComplexPKRelatedField):
            value = "\n".join(x.get("label", "") for x in value)
        elif isinstance(field, ChoiceField):
            value = dict(field.choices).get(value)
        elif isinstance(field, BooleanField):
            value = "是" if value else "否"
        elif isinstance(field, ListSerializer):
            value = [dict(x) for x in value]
        elif isinstance(field, BaseSerializer):
            value = dict(value)

        return value

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        ret = OrderedDict()
        fields = self.export_fields

        for field in fields:
            field.label = str(field.label)
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue
            except AttributeError:
                ret[field.label] = ""
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = (
                attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            )
            if check_for_none is None:
                ret[field.label] = None
            else:
                value = field.to_representation(attribute)
                ret[field.label] = self._trans_value(value, field)

        return ret
