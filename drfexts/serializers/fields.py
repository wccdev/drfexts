import collections
from collections import OrderedDict
from functools import cached_property

from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import (
    CharField,
    ChoiceField,
    Field,
    empty,
    flatten_choices_dict,
    get_attribute,
    to_choices_dict,
)
from rest_framework.relations import PrimaryKeyRelatedField, RelatedField
from rest_framework.serializers import Serializer
from rest_framework.utils import html
from rest_framework.utils.field_mapping import ClassLookupDict
from rest_framework.utils.serializer_helpers import BindingDict

__all__ = (
    "SequenceField",
    "DisplayChoiceField",
    "MultiSlugRelatedField",
    "IsNullField",
    "IsNotNullField",
    "ComplexPKRelatedField",
    "ChoiceObjectField",
    "MultipleChoiceObjectField",
)


class SequenceField(Field):
    """
    A read-only field that output increasing number started from zero.
    """

    cached_attr_name = "_curval"

    def __init__(self, start=1, step=1, **kwargs):
        self.start = start
        self.step = step
        kwargs["source"] = "*"
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def _incr(self):
        curval = getattr(self, self.cached_attr_name, self.start)
        setattr(self, self.cached_attr_name, curval + self.step)
        return curval

    def to_representation(self, value):
        return self._incr()


class DisplayChoiceField(ChoiceField):
    """
    Serialize: convert values into choice strings
    Deserialize: convert choice strings into values
    """

    def to_representation(self, value):
        if value in ("", None):
            return value
        return self.values_to_choice_strings.get(str(value), value)

    def _set_choices(self, choices):
        self.grouped_choices = to_choices_dict(choices)
        self._choices = flatten_choices_dict(self.grouped_choices)

        # Map the string representation of choices to the underlying value.
        # Allows us to deal with eg. integer choices while supporting either
        # integer or string input, but still get the correct datatype out.
        self.choice_strings_to_values = {
            str(label): value for value, label in self.choices.items()
        }
        self.values_to_choice_strings = dict(self.choices)

    choices = property(ChoiceField._get_choices, _set_choices)


class ChoiceSerializer(Serializer):
    id = CharField(label="值")
    label = CharField(required=False, label="键")
    color = CharField(required=False, label="颜色", allow_null=True)


@extend_schema_field(ChoiceSerializer())
class ChoiceObjectField(ChoiceField):
    def to_internal_value(self, data):
        if isinstance(data, dict):
            data = data.get("id")

        return super().to_internal_value(data)

    def to_representation(self, value):
        if value in ("", None):
            return None

        label = next(
            (v for k, v in self.choices.items() if str(k) == str(value)), str(value)
        )
        return {"id": value, "label": label, "color": getattr(label, "color", None)}


@extend_schema_field(ChoiceSerializer(many=True))
class MultipleChoiceObjectField(ChoiceObjectField):
    default_error_messages = {
        "invalid_choice": _('"{input}" is not a valid choice.'),
        "not_a_list": _('Expected a list of objects but got type "{input_type}".'),
        "empty": _("This selection may not be empty."),
    }
    default_empty_html = []

    def __init__(self, **kwargs):
        self.allow_empty = kwargs.pop("allow_empty", True)
        super().__init__(**kwargs)

    def get_value(self, dictionary):
        if self.field_name not in dictionary:
            if getattr(self.root, "partial", False):
                return empty
        # We override the default field access in order to support
        # lists in HTML forms.
        if html.is_html_input(dictionary):
            return dictionary.getlist(self.field_name)
        return dictionary.get(self.field_name, empty)

    def to_internal_value(self, data):
        if isinstance(data, str) or not hasattr(data, "__iter__"):
            self.fail("not_a_list", input_type=type(data).__name__)
        if not self.allow_empty and len(data) == 0:
            self.fail("empty")

        return {
            # Arguments for super() are needed because of scoping inside
            # comprehensions.
            super().to_internal_value(item)
            for item in data
        }

    def to_representation(self, value):
        return {super().to_representation(item) for item in value}


class MultiSlugRelatedField(RelatedField):
    """
    Represents a relationship using a unique set of fields on the target.
    """

    default_error_messages = {
        "does_not_exist": _("Object with {error_msg} does not exist."),
        "invalid": _("Invalid value."),
    }

    def __init__(self, slug_fields=None, **kwargs):
        assert slug_fields is not None, "The `slug_fields` argument is required."
        self.slug_fields = slug_fields
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, collections.Mapping):
            self.fail("invalid")
        if not set(data.keys()) == set(self.slug_fields):
            self.fail("invalid")
        try:
            instance = self.get_queryset().get(**data)
            return instance
        except ObjectDoesNotExist:
            lookups = ["=".join((lookup, value)) for lookup, value in data.items()]
            self.fail("does_not_exist", error_msg=" ".join(lookups))
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, value):
        return dict(
            zip(
                self.slug_fields,
                (getattr(value, slug_field) for slug_field in self.slug_fields),
            )
        )


class StringListField(serializers.ListField):
    child = serializers.CharField()


class IntegerListField(serializers.ListField):
    child = serializers.IntegerField()


class IsNullField(serializers.ReadOnlyField):
    default_error_messages = {"invalid": _("Must be a valid boolean.")}

    def to_representation(self, value):
        return value is None


class IsNotNullField(IsNullField):
    def to_representation(self, value):
        return value is not None


class ComplexPKRelatedField(PrimaryKeyRelatedField):
    display_field_custom = "label_field"
    display_field_default = "name"
    display_field_name = "label"

    def __init__(
        self,
        pk_field_name="id",
        fields=(),
        **kwargs,
    ):
        self.pk_field_name = pk_field_name
        self.extra_fields = fields
        self.instance = None
        super().__init__(**kwargs)

    @cached_property
    def fields(self):
        """
        A dictionary of {field_name: field_instance}.
        """
        # `fields` is evaluated lazily. We do this to ensure that we don't
        # have issues importing modules that use ModelSerializers as fields,
        # even if Django's app-loading stage has not yet run.
        fields = BindingDict(self)
        for key, value in self.get_fields().items():
            fields[key] = value
        return fields

    def get_fields(self):
        """
        Return the dict of field names -> field instances that should be
        used for `self.fields` when instantiating the serializer.
        """

        if self.queryset is not None:
            model = self.queryset.model
        else:
            assert hasattr(
                self.parent, "Meta"
            ), 'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
            assert hasattr(
                self.parent.Meta, "model"
            ), 'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )

            parent_model = getattr(self.parent.Meta, "model")
            model = parent_model._meta.get_field(self.source).related_model

        # Determine the fields that should be included on the serializer.
        fields = OrderedDict()
        field_mapping = ClassLookupDict(
            serializers.ModelSerializer.serializer_field_mapping
        )

        field_names = list(self.extra_fields).copy()
        # add Filter for label
        if self.display_field_name not in self.extra_fields:
            field_names = [self.display_field_name] + field_names

        for field_name in field_names:
            if field_name == self.pk_field_name:
                continue

            filter_filed = field_name
            kwargs = {"read_only": True}

            if field_name == self.display_field_name:
                filter_filed = self.display_field_name
                field_name = getattr(
                    model, self.display_field_custom, self.display_field_default
                )
                if field_name != filter_filed:
                    kwargs["source"] = field_name

            try:
                model_field = model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue

            fields[filter_filed] = field_mapping[model_field](
                label=model_field.verbose_name,
                help_text=model_field.help_text,
                **kwargs,
            )

        return fields

    def get_attribute(self, instance):
        self.instance = instance  # cache instance for `to_representation`
        return super().get_attribute(instance)

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            # Ensure that field.choices returns something sensible
            # even when accessed with a read-only field.
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict(
            [
                (
                    self.to_representation(item)[self.pk_field_name],
                    self.display_value(item),
                )
                for item in queryset
            ]
        )

    def to_internal_value(self, data):
        try:
            data = data[self.pk_field_name]
        except TypeError:
            pass

        return super().to_internal_value(data)

    def to_representation(self, value):
        try:
            attr_obj = get_attribute(
                self.instance, self.source_attrs
            )  # attr_obj is a `PKOnlyObject` instance
        except AttributeError:
            attr_obj = value  # attr_obj is a model instance

        data = {self.pk_field_name: super().to_representation(value)}
        if self.display_field_name not in self.extra_fields:
            display_field = getattr(
                attr_obj, self.display_field_custom, self.display_field_default
            )
            data[self.display_field_name] = getattr(
                attr_obj, display_field, str(attr_obj)
            )

        for field_name in self.extra_fields:
            data[field_name] = getattr(attr_obj, field_name, None)

        return data


class NullToEmptyCharField(serializers.CharField):
    def get_value(self, dictionary):
        value = super().get_value(dictionary)
        if not self.allow_null and value is None:
            value = ""

        return value
