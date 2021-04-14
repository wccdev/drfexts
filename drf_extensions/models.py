from itertools import chain

from django.db import models


class VirtualForeignKey(models.ForeignKey):
    """
    Virtual foreignkey which won't create concret relationship on database level.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_constraint", False)
        super().__init__(*args, **kwargs)


class VirtualManyToManyField(models.ManyToManyField):
    """
    Virtual many-to-many relation which won't create concret relationship on database level.
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("db_constraint", False)
        super().__init__(*args, **kwargs)


class ToDictModel(models.Model):
    def to_dict(self, fields=None, exclude=None, convert_choice=False, fields_map=None):
        """
        Return a dict containing the data in ``instance`` suitable for passing as
        a Form's ``initial`` keyword argument.

        ``fields`` is an optional list of field names. If provided, return only the
        named.

        ``exclude`` is an optional list of field names. If provided, exclude the
        named from the returned dict, even if they are listed in the ``fields``
        argument.

        ``translate_choice`` If provided, convert the value into display value.

        ``field_map`` is dict object, If provided, perform field name mapping.
        """
        opts = self._meta
        fields_map = fields_map or {}
        data = {}
        assert not all([fields, exclude]), "Cannot set both 'fields' and 'exclude' options."
        for f in chain(opts.concrete_fields, opts.private_fields):
            if fields and f.name not in fields:
                continue
            if exclude and f.name in fields:
                continue

            field_name = fields_map.get(f.name, f.name)
            if convert_choice and f.choices:
                data[field_name] = getattr(self, f'get_{f.name}_display')()
            else:
                data[field_name] = f.value_from_object(self)

        for f in opts.many_to_many:
            field_name = fields_map.get(f.name, f.name)
            data[field_name] = [i.id for i in f.value_from_object(self)]
        return data

    class Meta:
        abstract = True
