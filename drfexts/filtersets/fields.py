import operator
from functools import reduce

from django.db.models import Q
from django.forms import MultipleChoiceField
from django_filters import MultipleChoiceFilter, ModelMultipleChoiceFilter, CharFilter
from django_filters.constants import EMPTY_VALUES


class MultiSearchMixin:
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("lookup_expr", getattr(self, "lookup_expr", "icontains"))
        self.search_fields = kwargs.pop('search_fields', None)
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES or not value:
            return qs

        if self.distinct:
            qs = qs.distinct()

        if self.search_fields:
            queries = (Q(**{'%s__%s' % (search_field, self.lookup_expr): value}) for search_field in self.search_fields)
            conditions = reduce(operator.or_, queries)
            qs = qs.filter(conditions)
        else:
            lookup = '%s__%s' % (self.field_name, self.lookup_expr)
            qs = self.filter(**{lookup: value})

        return qs


class MultiSearchFilter(MultiSearchMixin, CharFilter):
    """
    This filter performs OR(by default) query on the multi fields.
    """

    ...


class MultipleChoiceSearchFilter(MultiSearchMixin, ModelMultipleChoiceFilter):
    """
    Extended MultipleChoiceSearchFilter
    """

    lookup_expr = 'in'


class NotDistinctMultipleChoiceFilter(MultipleChoiceFilter):
    def __init__(self, *args, **kwargs):
        self.choices = kwargs.get("choices")
        if not self.choices:
            raise ValueError('"choices" is a necessary parameter in this Filter')
        kwargs.setdefault("distinct", False)
        super(NotDistinctMultipleChoiceFilter, self).__init__(*args, **kwargs)

    def is_noop(self, qs, value):
        """
        穷举choice选项时，返回true，避免非必要的查询
        """
        if len(set(value)) == len(self.choices):
            return True
        return False


class MultipleValueField(MultipleChoiceField):
    def __init__(self, *args, field_class, **kwargs):
        self.inner_field = field_class()
        super().__init__(*args, **kwargs)

    def valid_value(self, value):
        return self.inner_field.validate(value)

    def clean(self, values):
        return values and [self.inner_field.clean(value) for value in values]

