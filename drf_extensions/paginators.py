import itertools
from urllib import parse

from django.core.paginator import InvalidPage, Paginator, EmptyPage, PageNotAnInteger
from django.utils.encoding import force_str
from rest_framework import pagination
from rest_framework.pagination import CursorPagination, _positive_int, _reverse_ordering
from rest_framework.response import Response
from rest_framework.settings import api_settings
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
            raise EmptyPage(_('That page contains no results'))
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
            raise PageNotAnInteger(_('That page number is not an integer'))
        if number < 1:
            raise EmptyPage(_('That page number is less than 1'))
        return number


class StandardResultsSetPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 10


class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response(
            {"total_count": (getattr(self, "page", 0) and self.page.paginator.count) or 0, "items": data}
        )


class WithoutCountPagination(CustomPagination):
    has_next: bool = True

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = WithoutCountPaginator(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages
        self.request = request

        try:
            self.page = paginator.page(page_number)
        except InvalidPage:
            return []

        return self.page

    def get_next_link(self):
        if not getattr(self, "page", 0) or not self.page.paginator.has_next_page:
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.next_page_number()
        return self.replace_query_param(url, self.page_query_param, page_number)

    def get_previous_link(self):
        if not getattr(self, "page", 0) or not self.page.paginator.has_previous_page:
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return self.remove_query_param(url, self.page_query_param)
        return self.replace_query_param(url, self.page_query_param, page_number)

    @staticmethod
    def replace_query_param(url, key, val):
        """
        Given a URL and a key/val pair, set or replace an item in the query
        parameters of the URL, and return the new URL.
        """
        (_, _, path, query, fragment) = parse.urlsplit(force_str(url))
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        query_dict[force_str(key)] = [force_str(val)]
        query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
        return parse.urlunsplit(("", "", path, query, fragment))

    @staticmethod
    def remove_query_param(url, key):
        """
        Given a URL and a key/val pair, remove an item in the query
        parameters of the URL, and return the new URL.
        """
        (_, _, path, query, fragment) = parse.urlsplit(force_str(url))
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        query_dict.pop(key, None)
        query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
        return parse.urlunsplit(("", "", path, query, fragment))

    def get_paginated_response(self, data):
        return Response({"list": data, "next": self.get_next_link(), "previous": self.get_previous_link()})


class BigPagePagination(CustomPagination):
    page_size = 5000
    page_size_query_param = "page_size"
    max_page_size = 100000


class CursorSetPagination(CursorPagination):
    page_size = 10
    max_page_size = 500
    page_size_query_param = "page_size"
    ordering = "-created_at"

    def paginate_queryset(self, queryset, request, view=None):
        page = super().paginate_queryset(queryset, request, view=view)
        self.base_url = request.get_full_path()
        return page

    def get_paginated_response(self, data):
        return Response({"previous": self.get_previous_link(), "next": self.get_next_link(), "list": data})


class LotPagination(CursorPagination):
    """
    The lot pagination implementation is necessarily complex.
    For an overview of the position/offset style we use, see this post:
    https://cra.mr/2011/03/08/building-cursors-for-the-disqus-api
    """

    lot_size = 25
    cursor_query_param = 'cursor'
    page_size = api_settings.PAGE_SIZE
    ordering = 'lot_no'

    # The offset in the cursor is used in situations where we have a
    # nearly-unique index. (Eg millisecond precision creation timestamps)
    # We guard against malicious users attempting to cause expensive database
    # queries, by having a hard cap on the maximum possible size of the offset.
    offset_cutoff = 1000

    def paginate_queryset(self, queryset, request, view=None):
        self.page_size = self.get_page_size(request)
        if not self.page_size:
            return None

        self.base_url = request.build_absolute_uri()
        self.ordering = self.get_ordering(request, queryset, view)

        self.cursor = self.decode_cursor(request)
        if self.cursor is None:
            (offset, reverse, current_position) = (0, False, None)
        else:
            (offset, reverse, current_position) = self.cursor

        # Cursor pagination always enforces an ordering.
        if reverse:
            queryset = queryset.order_by(*_reverse_ordering(self.ordering))
        else:
            queryset = queryset.order_by(*self.ordering)

        # If we have a cursor with a fixed position then filter by that.
        if current_position is not None:
            order = self.ordering[0]
            is_reversed = order.startswith('-')
            order_attr = order.lstrip('-')

            # Test for: (cursor reversed) XOR (queryset reversed)
            if self.cursor.reverse != is_reversed:
                kwargs = {order_attr + '__lt': current_position}
            else:
                kwargs = {order_attr + '__gt': current_position}

            queryset = queryset.filter(**kwargs)

        # If we have an offset cursor then offset the entire page by that amount.
        # We also always fetch an extra item in order to determine if there is a
        # page following on from this one.
        results = list(queryset[offset : offset + self.page_size + 1])

        self.page = list(self.get_fixed_page(results))
        # self.page = list(results[: self.page_size])

        # Determine the position of the final item following the page.
        if len(results) > len(self.page):
            has_following_position = True
            fixed_count = len(results) - len(self.page)
            following_position = self._get_position_from_instance(results[-fixed_count], self.ordering)
        else:
            has_following_position = False
            following_position = None

        if reverse:
            # If we have a reverse queryset, then the query ordering was in reverse
            # so we need to reverse the items again before returning them to the user.
            self.page = list(reversed(self.page))

            # Determine next and previous positions for reverse cursors.
            self.has_next = (current_position is not None) or (offset > 0)
            self.has_previous = has_following_position
            if self.has_next:
                self.next_position = current_position
            if self.has_previous:
                self.previous_position = following_position
        else:
            # Determine next and previous positions for forward cursors.
            self.has_next = has_following_position
            self.has_previous = (current_position is not None) or (offset > 0)
            if self.has_next:
                self.next_position = following_position
            if self.has_previous:
                self.previous_position = current_position

        # Display page controls in the browsable API if there is more
        # than one page.
        if (self.has_previous or self.has_next) and self.template is not None:
            self.display_page_controls = True

        return self.page

    def get_fixed_page(self, results):
        n = 1
        for k, group in itertools.groupby(results, lambda r: getattr(r, self.ordering)):
            if n > self.page_size:
                return

            for d in group:
                yield d

    def get_fixed_page_size(self, page_size):
        return page_size * self.lot_size

    def get_page_size(self, request):
        if self.page_size_query_param:
            try:
                positive_int = _positive_int(
                    request.query_params[self.page_size_query_param], strict=True, cutoff=self.max_page_size
                )
                return self.get_fixed_page_size(positive_int)

            except (KeyError, ValueError):
                pass

        return self.get_fixed_page_size(self.page_size)
