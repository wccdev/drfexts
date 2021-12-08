import re

from django import forms
from django.forms import Select
from django_filters.widgets import RangeWidget


class RangeListWidget(forms.MultiWidget):
    """
    Dealing with query paramm in url like:
        /api/user?created_at[]=2020-01-01&created_at[]=2020-02-01
    """

    template_name = 'django_filters/widgets/multiwidget.html'

    def __init__(self, attrs=None):
        widgets = (forms.TextInput, forms.TextInput)
        super().__init__(widgets, attrs)

    def value_from_datadict(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            getter = data.get

        return getter(name)

    def value_omitted_from_data(self, data, files, name):
        try:
            getter = data.getlist
        except AttributeError:
            return True

        return all(getter(name))

    def decompress(self, value):
        if value:
            return [value.start, value.stop]
        return [None, None]


class CustomSelectMultiple(Select):
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


class CustomRangeWidget(RangeWidget):
    """
    支持以下格式查询参数
    1. query/company/?a[0]=1&a[1]=10 -> data=[1,10]
    2. query/company/?a[0]=1& -> data=[1, None]
    3. query/company/?a[1]=10 -> data=[None, 10]
    4. query/company/?a=1 -> data=[1,1]

    转换成data=[1, 10]
    """

    suffixes = ['[0]', '[1]']

    def suffixed(self, name, suffix):
        return ''.join([name, suffix]) if suffix else name

    def value_from_datadict(self, data, files, name):
        return [
            widget.value_from_datadict(data, files, self.suffixed(name, suffix))
            or widget.value_from_datadict(data, files, name)
            for widget, suffix in zip(self.widgets, self.suffixes)
        ]

    def value_omitted_from_data(self, data, files, name):
        return all(
            widget.value_omitted_from_data(data, files, self.suffixed(name, suffix))
            or widget.value_omitted_from_data(data, files, name)
            for widget, suffix in zip(self.widgets, self.suffixes)
        )
