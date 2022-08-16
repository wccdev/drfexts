from urllib import parse

from django.core.paginator import InvalidPage
from django.utils.encoding import force_str
from rest_framework import pagination
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

from .paginators import WithoutCountPaginator


class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 5000

    def paginate_queryset(self, queryset, request, view=None):
        page_num = request.query_params.get(self.page_query_param)
        # 判断，如果 page 为all 则取消分页返回所有
        if page_num == "all":
            request.query_params._mutable = True
            request.query_params[self.page_query_param] = 1
            request.query_params[self.page_size_query_param] = self.max_page_size
            request.query_params._mutable = False

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return Response(
            {
                "total": self.page.paginator.count,
                "page_size": self.page.paginator.per_page,
                "current_page": self.page.number,
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "total": {
                    "type": "integer",
                    "example": 123,
                },
                "page_size": {
                    "type": "integer",
                    "example": 15,
                },
                "current_page": {
                    "type": "integer",
                    "example": 1,
                },
                "results": schema,
            },
        }


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
        return Response(
            {
                "list": data,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            }
        )


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
        return Response(
            {
                "previous": self.get_previous_link(),
                "next": self.get_next_link(),
                "list": data,
            }
        )
