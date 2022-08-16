from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.utils.translation import gettext_lazy as _


class WithoutCountPaginator(Paginator):
    """
    This is a PAGINATOR, NOT PAGINATION
    """

    has_next_page: bool = True
    has_previous_page: bool = False

    def page(self, number):
        number = self.validate_number(number)
        self.has_previous_page = False if number == 1 else True
        bottom = (number - 1) * self.per_page
        top = bottom + self.per_page
        top_with_extra = top + 1
        object_with_extra = list(self.object_list[bottom:top_with_extra])
        if not object_with_extra:
            raise EmptyPage(_("That page contains no results"))
        if len(object_with_extra) >= self.per_page:
            object_with_extra = object_with_extra[:-1]
            self.has_next_page = True
        else:
            self.has_next_page = False
        return self._get_page(object_with_extra, number, self)

    @property
    def count(self):
        return 0

    def validate_number(self, number):
        """Validate the given 1-based page number."""
        try:
            if isinstance(number, float) and not number.is_integer():
                raise ValueError
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger(_("That page number is not an integer"))
        if number < 1:
            raise EmptyPage(_("That page number is less than 1"))
        return number
