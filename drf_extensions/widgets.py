from django import forms


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