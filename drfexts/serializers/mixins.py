from rest_framework import serializers

from drfexts.models import AuditModel


class DynamicFieldsSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)

        # Instantiate the superclass normally
        super(DynamicFieldsSerializer, self).__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class AuditSerializerMixin:
    """
    增强DRF的ModelSerializer,可自动更新模型的审计字段记录
    """

    created_by_field_name = 'created_by'  # 创建人的审计字段名称, 默认created_by, 继承使用时可自定义覆盖
    updated_by_field_name = 'updated_by'  # 修改人的审计字段名称, 默认updated_by, 继承使用时可自定义覆盖

    created_by_name = serializers.SlugRelatedField(slug_field="username", source=created_by_field_name, read_only=True, label="创建人")
    updated_by_name = serializers.SlugRelatedField(slug_field="username", source=updated_by_field_name, read_only=True, label="修改人")

    def create(self, validated_data):
        request = self.context.get('request')  # noqa
        if request and self.created_by_field_name in self.fields:  # noqa
            validated_data[self.created_by_field_name] = request.user

        if request and self.updated_by_field_name in self.fields:  # noqa
            validated_data[self.updated_by_field_name] = request.user

    def update(self, instance, validated_data):
        request = self.context.get('request')  # noqa
        if request and self.updated_by_field_name in self.fields:  # noqa
            validated_data[self.updated_by_field_name] = request.user

        return super().update(instance, validated_data)  # noqa
