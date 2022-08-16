import re

from django.forms import Select, TextInput
from django.utils.datastructures import MultiValueDict
from django_filters.widgets import QueryArrayWidget, RangeWidget


class ExtendedSelectMultiple(Select):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        values = list()
        pattern = rf"{name}(\[\d*\])?"
        for k, v in data.items():
            if re.fullmatch(pattern, k):
                values.append(v)
        return values

    def value_omitted_from_data(self, data, files, name):
        # An unselected <select multiple> doesn't appear in POST data, so it's
        # never known if the value is actually omitted.
        return False


class FixedQueryArrayWidget(QueryArrayWidget):
    """
    Enables request query array notation that might be consumed by MultipleChoiceFilter

    1. Values can be provided as csv string:  ?foo=bar,baz
    2. Values can be provided as query array: ?foo[]=bar&foo[]=baz
    3. Values can be provided as query array: ?foo=bar&foo=baz

    Note: Duplicate and empty values are skipped from results
    """

    def value_from_datadict(self, data, files, name):
        if not isinstance(data, MultiValueDict):
            data = MultiValueDict(data)

        values_list = data.getlist(name, data.getlist("%s[]" % name)) or []

        # treat value as csv string: ?foo=1,2
        if len(values_list) == 1:
            ret = [x.strip() for x in values_list[0].rstrip(",").split(",") if x]
        # apparently its an array, so no need to process it's values as csv
        # ?foo=1&foo=2 -> data.getlist(foo) -> foo = [1, 2]
        # ?foo[]=1&foo[]=2 -> data.getlist(foo[]) -> foo = [1, 2]
        elif len(values_list) > 1:
            ret = [x for x in values_list if x]
        else:
            ret = []

        return list(set(ret))


class ExtendedRangeWidget(RangeWidget):
    """
    支持以下格式查询参数
    1. query/company/?a_min=1&a_max=10 -> data=[1,10]
    2. query/company/?a_min=1 -> data=[1, None]
    3. query/company/?a_max=10 -> data=[None, 10]
    4. query/company/?a=1 -> data=[1,1]
    """

    def value_from_datadict(self, data, files, name):
        return [
            widget.value_from_datadict(data, files, self.suffixed(name, suffix))
            or widget.value_from_datadict(data, files, name)
            for widget, suffix in zip(self.widgets, self.suffixes)
        ]


class ExtendedDateRangeWidget(ExtendedRangeWidget):
    suffixes = ["after", "before"]


class LookupTextInput(TextInput):
    suffix = "equal"
    default_lookup_expr = "icontains"

    def suffixed(self, name):
        return f"{name}_{self.suffix}"

    def value_from_datadict(self, data, files, name):
        """
        Given a dictionary of data and this widget's name, return the value
        of this widget or None if it's not provided.
        """
        if self.suffixed(name) in data:
            value = data.get(self.suffixed(name))
            lookup_expr = "exact"
        else:
            value = data.get(name)
            lookup_expr = self.default_lookup_expr

        return f"{value}:{lookup_expr}"
