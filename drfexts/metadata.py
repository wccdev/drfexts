"""
The metadata API is used to allow customization of how `OPTIONS` requests
are handled. We currently provide a single default implementation that returns
some fairly ad-hoc information about the view.
Future implementations might use JSON schema or other definitions in order
to return this information in a more standardized way.
"""
from rest_framework.fields import ChoiceField, MultipleChoiceField
from rest_framework.metadata import BaseMetadata
from django.core.exceptions import PermissionDenied
from django.http import Http404
import copy
from django.utils.encoding import force_str
from rest_framework import exceptions, serializers
from rest_framework.request import clone_request
from rest_framework.utils.field_mapping import ClassLookupDict
from .style import Style
from .utils import to_table_choices

SIMPLE = 'simple'
COMPLEX = 'subtable'


class TableMeta(dict):
    __slots__ = ('expand', 'table_type', 'fields', 'data_field')

    def __init__(self, table_type=SIMPLE, expand=False, **kwargs):
        self.expand = expand
        if table_type not in (SIMPLE, COMPLEX):
            raise ValueError('Unknown table type.')
        self.table_type = table_type
        _ = dict()
        for attr in self.__slots__:
            if getattr(self, attr, None):
                _.update({attr: getattr(self, attr)})
        super().__init__(_, **kwargs)


class VueTableMetadata(BaseMetadata):
    """
    This is the default metadata implementation.
    It returns an ad-hoc set of information about the view.
    There are not any formalized standards for `OPTIONS` responses
    for us to base this on.
    """

    style_class = Style
    label_lookup = ClassLookupDict(
        {
            serializers.Field: 'field',
            serializers.BooleanField: 'boolean',
            serializers.NullBooleanField: 'boolean',
            serializers.CharField: 'string',
            serializers.UUIDField: 'string',
            serializers.URLField: 'url',
            serializers.EmailField: 'email',
            serializers.RegexField: 'regex',
            serializers.SlugField: 'slug',
            serializers.IntegerField: 'integer',
            serializers.FloatField: 'float',
            serializers.DecimalField: 'decimal',
            serializers.DateField: 'date',
            serializers.DateTimeField: 'datetime',
            serializers.TimeField: 'time',
            serializers.ChoiceField: 'choice',
            serializers.MultipleChoiceField: 'multiple choice',
            serializers.FileField: 'file upload',
            serializers.ImageField: 'image upload',
            serializers.ListField: 'list',
            serializers.DictField: 'nested object',
            serializers.Serializer: 'nested object',
        }
    )

    search_type_lookup = ClassLookupDict(
        {
            serializers.Field: 'input',
            serializers.BooleanField: 'select',
            serializers.NullBooleanField: 'select',
            serializers.IntegerField: 'num',
            serializers.FloatField: 'input',
            serializers.DecimalField: 'input',
            serializers.DateField: 'date',
            serializers.DateTimeField: 'date',
            serializers.TimeField: 'date',
            serializers.ChoiceField: 'select',
            serializers.MultipleChoiceField: 'select',
        }
    )

    def determine_metadata(self, request, view):
        metadata = dict()
        metadata['name'] = view.get_view_name()
        metadata['description'] = view.get_view_description()
        metadata['renders'] = [renderer.media_type for renderer in view.renderer_classes]
        metadata['parses'] = [parser.media_type for parser in view.parser_classes]
        if hasattr(view, 'get_serializer'):
            actions = self.determine_actions(request, view)
            if actions:
                metadata['actions'] = actions
        return metadata

    def determine_actions(self, request, view):
        """
        For generic class based views we return information about
        the fields that are accepted for 'PUT' and 'POST' methods.
        """
        setattr(self, "request", request)
        setattr(self, "view", view)
        actions = {}
        action_names = []
        extra_actions = view.get_extra_actions()
        extra_action_names = [
            act.mapping['get']
            for act in extra_actions
            if 'get' in act.mapping and act.mapping['get'] not in ("export", "meta")
        ]
        if 'get' in view.action_map:
            action_names = [view.action_map["get"]] + extra_action_names

        for action in action_names:
            actions[action] = dict()
            origin_action = view.action
            view.action = action
            serializer = view.get_serializer()
            actions[action]["meta"] = self.get_serializer_meta(view, serializer)
            actions[action]["columns"] = self.get_serializer_info(serializer)
            view.action = origin_action

        # TODO check permissions
        # for method in {'GET'} & set(view.allowed_methods):
        #     view.request = clone_request(request, method)
        #     try:
        #         # Test global permissions
        #         if hasattr(view, 'check_permissions'):
        #             view.check_permissions(view.request)
        #     except (exceptions.APIException, PermissionDenied, Http404):
        #         pass
        #     else:
        #         # If user has appropriate permissions for the view, include
        #         # appropriate metadata about the fields that should be supplied.
        #         serializer = view.get_serializer()
        #         actions[method] = self.get_serializer_info(serializer)
        #     finally:
        #         view.request = request

        return actions

    def get_serializer_meta(self, view, serializer):
        """
        :param view: [description]
        :type view: [type]
        :param serializer: [description]
        :type serializer: [type]
        """
        table_meta = getattr(view, "table_meta", {})
        data_field_name = table_meta.get('data_field')
        data_field = serializer.fields.get(data_field_name)
        if data_field and hasattr(data_field, "child"):
            table_meta['fields'] = self.get_serializer_info(data_field.child)

        return table_meta

    def get_serializer_info(self, serializer):
        """
        Given an instance of a serializer, return a dictionary of metadata
        about its fields.
        """
        if hasattr(serializer, 'child'):
            # If this is a `ListSerializer` then we want to examine the
            # underlying child serializer instance instead.
            serializer = serializer.child

        return [
            self.get_field_style(field)
            for field_name, field in serializer.fields.items()
            if not isinstance(field, serializers.HiddenField) and not field.write_only
        ]

    def get_field_style(self, field, sub_table=True):
        """
        Given an instance of a serializer field, return a dictionary
        of metadata about it.
        """
        # validate style
        if isinstance(field.style, dict):
            copy_style = copy.deepcopy(field.style)
            style = self.style_class(**copy_style)
        elif isinstance(field.style, self.style_class):
            style = field.style
        else:
            raise ValueError("Unsupported style type.")

        style.field = field.field_name
        style.title = field.label

        if isinstance(field, (ChoiceField, MultipleChoiceField)) and field.choices:
            style.cellRender = to_table_choices(field.choices)

        return style.dict(exclude_none=True)
