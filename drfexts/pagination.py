from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response
from django.core.paginator import EmptyPage, PageNotAnInteger
from rest_framework.exceptions import NotFound
from urllib.parse import urlparse, urlunparse

from django.http import QueryDict


class CustomPagination(PageNumberPagination):
    # 默认每页显示的条目数
    page_size = 20

    # 允许客户端通过查询参数设置每页条目数
    page_size_query_param = "page_size"

    # 设置每页条目数的最大值
    max_page_size = 100000

    # 设置页码的查询参数名称
    page_query_param = "page"

    def paginate_queryset(self, queryset, request, view=None):
        """
        重写分页查询方法，支持page=all参数
        """
        # 获取page参数的值
        page_param = request.query_params.get(self.page_query_param)

        if page_param == "all":
            # 如果page=all，返回所有数据，不进行分页
            self.page = None
            self.request = request
            return list(queryset)

        try:
            # 尝试执行默认的分页逻辑
            return super().paginate_queryset(queryset, request, view)
        except (NotFound, EmptyPage, PageNotAnInteger):
            # 如果页码超出范围或无效，返回空列表
            self.page = None
            self.request = request
            self._empty_page = True  # 标记这是一个空页面
            return []

    def get_paginated_response(self, data):
        """
        重写分页响应方法，返回自定义格式
        """
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

    def get_previous_link(self):
        """
        获取上一页链接，如果没有上一页返回None
        """
        if not self.page.has_previous():
            return None

        page_number = self.page.previous_page_number()
        return self.get_page_link(page_number)

    def get_next_link(self):
        """
        获取下一页链接，如果没有下一页返回None
        """
        if not self.page.has_next():
            return None

        page_number = self.page.next_page_number()
        return self.get_page_link(page_number)

    def get_page_link(self, page_number):
        """
        构建页面链接
        """
        url = self.request.build_absolute_uri()
        return self.replace_query_param(url, self.page_query_param, page_number)

    def replace_query_param(self, url, key, val):
        """
        替换URL中的查询参数
        """

        parsed = urlparse(url)
        query_dict = QueryDict(parsed.query, mutable=True)
        query_dict[key] = val

        return urlunparse(
            (
                "",
                "",
                parsed.path,
                parsed.params,
                query_dict.urlencode(),
                parsed.fragment,
            )
        )

    def get_paginated_response(self, data):
        """
        重写分页响应方法，返回自定义格式
        """
        if self.page is None:
            # 如果page=all，返回所有数据，previous和next为空字符串
            return Response(
                {
                    "previous": "",
                    "next": "",
                    "results": data,
                }
            )
        # 正常分页情况，返回自定义格式
        return Response(
            {
                "previous": self.get_previous_link(),
                "next": self.get_next_link(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "previous": {
                    "type": "string",
                    "example": "/api/users/?page_size=10&page=1",
                },
                "next": {
                    "type": "string",
                    "example": "/api/users/?page_size=10&page=3",
                },
                "results": schema,
            },
        }


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
