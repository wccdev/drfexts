import collections
from functools import cached_property

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.fields import CharField
from rest_framework.fields import ChoiceField
from rest_framework.fields import empty
from rest_framework.fields import Field
from rest_framework.fields import flatten_choices_dict
from rest_framework.fields import get_attribute
from rest_framework.fields import SkipField
from rest_framework.fields import to_choices_dict
from rest_framework.relations import ManyRelatedField
from rest_framework.relations import PKOnlyObject
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.relations import RelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Serializer
from rest_framework.utils import html

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
    label = CharField(required=False, read_only=True, label="键")
    color = CharField(required=False, read_only=True, label="颜色", allow_null=True)


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
        serializer = self.get_serializer()
        return serializer.fields

    def get_model(self):
        """
        Return the model instance that should be used for the field.
        """
        if self.queryset is not None:
            model = self.queryset.model
        else:
            if isinstance(self.parent, ManyRelatedField):
                parent = self.parent.parent
                source = self.parent.source
            else:
                parent = self.parent
                source = self.source

            assert hasattr(
                parent, "Meta"
            ), f'Class {self.__class__.__name__} missing "Meta" attribute'

            assert hasattr(
                parent.Meta, "model"
            ), f'Class {self.__class__.__name__} missing "Meta.model" attribute'

            parent_model = parent.Meta.model
            model = parent_model._meta.get_field(source).related_model

        return model

    def get_serializer(self, *args, **kwargs):
        """
        Override `get_serializer` to pass the `fields
        """
        _model = self.get_model()
        display_field_name = getattr(
            _model, self.display_field_custom, self.display_field_default
        )
        if not hasattr(_model, display_field_name):
            display_field_name = "__str__"

        read_only_fields_nopk = list(set(self.extra_fields) - {self.pk_field_name})

        class NestedSerializer(ModelSerializer):
            label = serializers.CharField(source=display_field_name, read_only=True)

            class Meta:
                model = _model
                fields = [self.pk_field_name, "label", *self.extra_fields]
                read_only_fields = read_only_fields_nopk
                extra_kwargs = {
                    self.pk_field_name: {"read_only": False, "default": None},
                }

        return NestedSerializer(*args, **kwargs)

    def get_fields(self):
        """
        Return the dict of field names -> field instances that should be
        used for `self.fields` when instantiating the serializer.
        """
        serializer = self.get_serializer()
        return serializer.fields

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

        return [
            (
                self.to_representation(item)[self.pk_field_name],
                self.display_value(item),
            )
            for item in queryset
        ]

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

        if attr_obj is None:
            return {self.pk_field_name: value.pk, "label": ""}

        data = {self.pk_field_name: None, "label": ""}
        for field in self.fields.values():
            try:
                attribute = field.get_attribute(attr_obj)
            except SkipField:
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
                data[field.field_name] = None
            else:
                data[field.field_name] = field.to_representation(attribute)

        return data


class NullToEmptyCharField(serializers.CharField):
    def get_value(self, dictionary):
        value = super().get_value(dictionary)
        if not self.allow_null and value is None:
            value = ""

        return value
