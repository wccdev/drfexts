import collections

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.relations import RelatedField
from rest_framework.fields import Field, ChoiceField, to_choices_dict, flatten_choices_dict

__all__ = (
    "SequenceField",
    "DisplayChoiceField",
    "MultiSlugRelatedField",
)


class SequenceField(Field):
    """
    A read-only field that output increasing number started from zero.
    """

    cached_attr_name = '_curval'

    def __init__(self, start=1, step=1, **kwargs):
        self.start = start
        self.step = step
        kwargs['source'] = '*'
        kwargs['read_only'] = True
        super().__init__(**kwargs)

    def _incr(self):
        curval = getattr(self, self.cached_attr_name, self.start)
        setattr(self, self.cached_attr_name, curval + self.step)
        return curval

    def to_representation(self, value):
        return self._incr()


class DisplayChoiceField(ChoiceField):
    """
    Serialize: convert value into choice strings
    Deserialize: convert choice strings into value
    """
    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.display_strings_to_value[str(data)]
        except KeyError:
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if value in ('', None):
            return value
        return self.value_to_display_strings.get(str(value), value)

    def _get_choices(self):
        return self._choices

    def _set_choices(self, choices):
        self.grouped_choices = to_choices_dict(choices)
        self._choices = flatten_choices_dict(self.grouped_choices)
        # Map the string representation of choices to the underlying value.
        # Allows us to deal with eg. integer choices while supporting either
        # integer or string input, but still get the correct datatype out.
        self.value_to_display_strings = {
            str(key): value for key, value in self.choices.items()
        }
        self.display_strings_to_value = {
            str(value): key for key, value in self.choices.items()
        }

    choices = property(_get_choices, _set_choices)


class MultiSlugRelatedField(RelatedField):
    """
    Represents a relationship using a unique set of fields on the target.
    """

    default_error_messages = {
        'does_not_exist': _("Object with {error_msg} does not exist."),
        'invalid': _('Invalid value.'),
    }

    def __init__(self, slug_fields=None, **kwargs):
        assert slug_fields is not None, 'The `slug_fields` argument is required.'
        self.slug_fields = slug_fields
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if not isinstance(data, collections.Mapping):
            self.fail('invalid')
        if not set(data.keys()) == set(self.slug_fields):
            self.fail('invalid')
        try:
            instance = self.get_queryset().get(**data)
            return instance
        except ObjectDoesNotExist:
            lookups = ['='.join((lookup, value)) for lookup, value in data.items()]
            self.fail('does_not_exist', error_msg=' '.join(lookups))
        except (TypeError, ValueError):
            self.fail('invalid')

    def to_representation(self, value):
        return dict(zip(self.slug_fields, (getattr(value, slug_field) for slug_field in self.slug_fields)))


class StringListField(serializers.ListField):
    child = serializers.CharField()


class IntegerListField(serializers.ListField):
    child = serializers.IntegerField()


class IsNullField(serializers.ReadOnlyField):
    default_error_messages = {
        'invalid': _('Must be a valid boolean.')
    }

    def to_representation(self, value):
        return value is None


class IsNotNullField(IsNullField):

    def to_representation(self, value):
        return value is not None
