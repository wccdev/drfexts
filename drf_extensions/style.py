from collections import OrderedDict
from typing import Dict, List, Optional

from django.utils.encoding import force_str
from rest_framework import serializers
from rest_framework.utils.field_mapping import ClassLookupDict

sentinel = object()

INPUT_TYPE_NONE = None  # 不支持搜索
INPUT_TYPE_INPUT = "input"
INPUT_TYPE_SELECT = "select"
INPUT_TYPE_NUMBER = "num"
INPUT_TYPE_DATE = "date"
INPUT_TYPE_DATETIME = "datetime"
INPUT_TYPE_CHOICE = "select"
INPUT_TYPE_MULTI_CHOICE = "multi_select"


label_lookup = ClassLookupDict(
    {
        serializers.Field: "field",
        serializers.BooleanField: "boolean",
        serializers.NullBooleanField: "boolean",
        serializers.CharField: "string",
        serializers.UUIDField: "string",
        serializers.URLField: "url",
        serializers.EmailField: "email",
        serializers.RegexField: "regex",
        serializers.SlugField: "slug",
        serializers.IntegerField: "integer",
        serializers.FloatField: "float",
        serializers.DecimalField: "decimal",
        serializers.DateField: "date",
        serializers.DateTimeField: "datetime",
        serializers.TimeField: "time",
        serializers.ChoiceField: "choice",
        serializers.MultipleChoiceField: "multiple choice",
        serializers.FileField: "file upload",
        serializers.ImageField: "image upload",
        serializers.ListField: "list",
        serializers.DictField: "nested object",
        serializers.Serializer: "nested object",
    }
)


search_type_lookup = ClassLookupDict(
    {
        serializers.CharField: INPUT_TYPE_INPUT,
        serializers.BooleanField: INPUT_TYPE_CHOICE,
        serializers.NullBooleanField: INPUT_TYPE_CHOICE,
        serializers.IntegerField: INPUT_TYPE_NUMBER,
        serializers.FloatField: INPUT_TYPE_INPUT,
        serializers.DecimalField: INPUT_TYPE_INPUT,
        serializers.DateField: INPUT_TYPE_DATE,
        serializers.DateTimeField: INPUT_TYPE_DATE,
        serializers.TimeField: INPUT_TYPE_DATE,
        serializers.ChoiceField: INPUT_TYPE_CHOICE,
        serializers.MultipleChoiceField: INPUT_TYPE_MULTI_CHOICE,
    }
)

search_key_lookup = ClassLookupDict(
    {
        serializers.Field: "icontains",
        serializers.BooleanField: "",
        serializers.NullBooleanField: "",
        serializers.CharField: "icontains",
        serializers.UUIDField: "icontains",
        serializers.URLField: "icontains",
        serializers.EmailField: "icontains",
        serializers.RegexField: "regex",
        serializers.SlugField: "slug",
        serializers.IntegerField: "",
        serializers.FloatField: "",
        serializers.DecimalField: "",
        serializers.DateField: "range",
        serializers.DateTimeField: "range",
        serializers.TimeField: "time",
        serializers.ChoiceField: "",
        serializers.MultipleChoiceField: "",
    }
)


class DisplayStyle(dict):
    __slots__ = (
        "column_title",
        "column_key",
        "column_align",
        "column_customer_width",
        "column_fixed",
        "column_visible",
        "column_editable",
        "column_sortable",
        "column_search_type",
        "column_search_key",
        "column_search_placeholder",
        "column_show_customize",
        "select_options_type",
        "select_options_value",
        "select_post_url",
        "select_post_data",
        "select_post_key",
        "select_post_name",
        "column_tooltip",
        "group_by_column",
        "child",
        "children",
    )

    def __init__(
        self,
        column_title: str = sentinel,
        column_key: str = sentinel,
        column_align: str = sentinel,
        column_customer_width: int = sentinel,
        column_search_type: str = sentinel,
        column_search_key: str = sentinel,
        column_search_placeholder: str = sentinel,
        column_show_customize: dict = sentinel,
        select_options_type: bool = sentinel,
        select_options_value: str = sentinel,
        select_post_url: str = sentinel,
        select_post_data: str = sentinel,
        select_post_key: str = sentinel,
        select_post_name: str = sentinel,
        column_tooltip: bool = sentinel,
        column_fixed: bool = sentinel,
        column_visible: bool = True,
        column_editable: bool = False,
        column_sortable: bool = False,
        group_by_column: str = sentinel,
        **kwargs
    ):
        self.column_title = column_title
        self.column_key = column_key
        self.column_align = column_align
        self.column_customer_width = column_customer_width
        self.column_fixed = column_fixed
        self.column_visible = column_visible
        self.column_editable = column_editable
        self.column_sortable = column_sortable
        self.column_search_type = column_search_type
        self.column_search_key = column_search_key
        self.column_search_placeholder = column_search_placeholder
        self.column_show_customize = column_show_customize
        self.select_options_type = select_options_type
        self.select_options_value = select_options_value
        self.select_post_url = select_post_url
        self.select_post_data = select_post_data
        self.select_post_key = select_post_key
        self.select_post_name = select_post_name
        self.column_tooltip = column_tooltip
        self.group_by_column = group_by_column
        d = dict()
        for attr in self.__slots__:
            if getattr(self, attr, sentinel) is not sentinel:
                d.update({attr: getattr(self, attr)})
        super().__init__(d, **kwargs)

    @property
    def is_api_select(self):
        return "select_options_type" in self and not self["select_options_type"]

    def set_column_title(self, metacls, field):
        """
        列显示的标题
        """
        self["column_title"] = field.label

    def set_column_key(self, metacls, field):
        """
        列内容的字段key, 即接口返回的数据字段名称
        """
        self["column_key"] = field.field_name

    def set_column_align(self, metacls, field):
        """
        列对齐方式:
          - left
          - right
          - center
        """
        ...

    def set_column_customer_width(self, metacls, field):
        """
        用户自定义列宽，字符串型数字
        """
        ...

    def set_column_fixed(self, metacls, field):
        """
        当前列是否固定,非必填,不填表示不固定
        options: [left, right]
        """
        ...

    def set_column_visible(self, metacls, field):
        """
        当前列是否显示
        """
        ...

    def set_column_editable(self, metacls, field):
        """
        列是否支持编辑
        rtype: bool
        """
        ...

    def set_column_sortable(self, metacls, field):
        """
        列是否支持排序
        """
        if isinstance(field, (serializers.SerializerMethodField, serializers.Serializer)):
            self["column_sortable"] = False
        elif isinstance(field, (serializers.DateField, serializers.DateTimeField)):
            self["column_sortable"] = True

    def set_column_search_type(self, metacls, field):
        """
        列搜索类型，默认空不搜索
        input: 为搜索框，
        select: 下拉选择，
        date: 为时间选择器，
        num: 为数字区间
        """
        if "column_search_type" not in self:
            try:
                if "set_select_post_url" in self:
                    self["column_search_type"] = INPUT_TYPE_SELECT
                else:
                    self["column_search_type"] = search_type_lookup[field]
            except KeyError:
                pass

    def set_column_search_key(self, metacls, field):
        """
        搜索的key值, 非必填
        """
        ...
        # [
        #     (field.source.replace(".", "__") or field_name, field.label)
        #     for field_name, field in serializer_class(context=context).fields.items()
        #     if not getattr(field, "write_only", False) and not field.source == "*"
        # ]

    def set_column_search_placeholder(self, metacls, field):
        """
        输入框提示语, 非必填
        """
        ...

    def set_column_show_customize(self, metacls, field):
        """
        自定义列值，前端处理数据，后端只需要传值
        """
        ...

    def set_select_options_type(self, metacls, field):
        """
        表头下拉选项的值
          - true: 取optionKey的缓冲key值
          - false: 走接口的请求参数
        """
        ...

    def set_select_options_value(self, metacls, field):
        """
        key值, 有两种情况取值不同
        1. 字段提供choices属性
        2. 布尔类型
        """
        if hasattr(field, "choices") and not isinstance(field, serializers.RelatedField):
            self["select_options_value"] = [
                dict(name=force_str(name, strings_only=True), value=value) for value, name in field.choices.items()
            ]
        elif isinstance(field, (serializers.BooleanField, serializers.NullBooleanField)):
            self["select_options_value"] = [{"name": "true", "value": True}, {"name": "false", "value": False}]

    def set_select_post_url(self, metacls, field):
        """
        下拉接口的请求接口
        select_options_type为false时必传
        """
        ...

    def set_select_post_data(self, metacls, field):
        """
        下拉接口的请求接口参数参数
        """
        if self.is_api_select and "select_post_name" not in self:
            self["select_post_key"] = "name"

    def set_select_post_key(self, metacls, field):
        """
        下拉接口的请求key的对应的数据字段名
        """
        ...

    def set_select_post_name(self, metacls, field):
        """
        下拉接口的请求name的对应的数据字段名
        """
        if self.is_api_select and "select_post_name" not in self:
            self["select_post_name"] = "name"

    def set_column_tooltip(self, metacls, field):
        """
        文本溢出隐藏后是否显示提示框
        """
        ...
