# drfexts

[![GitHub license](https://img.shields.io/github/license/aiden520/drfexts)](https://github.com/aiden520/drfexts/blob/master/LICENSE)
[![pypi-version](https://img.shields.io/pypi/v/drfexts.svg)](https://pypi.python.org/pypi/drfexts)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/drfexts)
[![PyPI - Django Version](https://img.shields.io/badge/django-%3E%3D4.2-44B78B)](https://www.djangoproject.com/)
[![PyPI - DRF Version](https://img.shields.io/badge/djangorestframework-%3E%3D3.12-red)](https://www.django-rest-framework.org)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

**Django REST Framework 企业级扩展工具集** — 提供模型基类、序列化器、视图集、自动过滤器、分页、数据导入导出、统一响应格式等开箱即用的组件，大幅减少 DRF 项目中的重复代码。

## 安装

```bash
pip install drfexts
```

或使用 Poetry：

```bash
poetry add drfexts
```

### 依赖要求

- Python >= 3.8
- Django >= 4.2
- djangorestframework >= 3.12.4
- django-filter >= 21.1
- django-storages >= 1.12.3
- djangorestframework-csv >= 2.1.1
- openpyxl >= 3.0.9
- orjson >= 3.8.0
- django-currentuser >= 0.5.3
- drf-flex-fields >= 0.9.8

---

## 目录

- [模型字段 (fields)](#模型字段-fields)
- [抽象模型基类 (models)](#抽象模型基类-models)
- [状态与选择 (choices)](#状态与选择-choices)
- [序列化器 (serializers)](#序列化器-serializers)
- [视图集 (viewsets)](#视图集-viewsets)
- [自动过滤器 (filtersets)](#自动过滤器-filtersets)
- [分页 (pagination)](#分页-pagination)
- [渲染器 (renderers)](#渲染器-renderers)
- [解析器 (parsers)](#解析器-parsers)
- [数据导出 (export)](#数据导出-export)
- [认证 (authentication)](#认证-authentication)
- [异常处理 (exceptions)](#异常处理-exceptions)
- [路由 (routers)](#路由-routers)
- [存储后端 (storages)](#存储后端-storages)
- [工具函数 (utils)](#工具函数-utils)

---

## 模型字段 (fields)

`drfexts.fields` 对 Django 原生字段进行了增强封装，所有字段自动设置 `help_text` 和 `db_comment`（来自 `verbose_name`），减少重复配置。

### 基础字段

所有基础字段与 Django 原生字段用法一致，但自动继承 `DefaultHelpTextMixin`，会将 `verbose_name` 同步为 `help_text` 和 `db_comment`。

可用字段：`AutoField`, `BigAutoField`, `CharField`, `TextField`, `IntegerField`, `BigIntegerField`, `SmallIntegerField`, `PositiveSmallIntegerField`, `BooleanField`, `FileField`, `ImageField`, `FilePathField`, `FloatField`, `DecimalField`, `DateTimeField`, `DateField`, `TimeField`, `DurationField`, `EmailField`, `URLField`, `IPAddressField`, `UUIDField`, `JSONField`

```python
from drfexts.fields import CharField, IntegerField, DecimalField

class Product(models.Model):
    name = CharField("商品名称", max_length=128)
    price = DecimalField("价格", max_digits=10, decimal_places=2)
    stock = IntegerField("库存")
```

### 审计字段

自动记录创建/修改时间和操作人：

| 字段 | 说明 |
|------|------|
| `CreatedAtField()` | 创建时间，`auto_now_add=True` |
| `UpdatedAtField()` | 修改时间，`auto_now=True` |
| `CreatedByField()` | 创建人，自动记录当前用户（基于 `django-currentuser`） |
| `UpdatedByField()` | 修改人，自动记录当前用户（`on_update=True`） |

### 状态字段

| 字段 | 对应选择类 | 说明 |
|------|-----------|------|
| `StatusField()` | `CommonStatus` | 完整生命周期状态（已删除/待提交/待生效/暂停中/已生效/待失效/已失效） |
| `SimpleStatusField()` | `SimpleStatus` | 简单二态状态（生效中/已失效） |
| `AuditStatusField()` | `AuditStatus` | 审核状态（三级审核：待审核/通过/驳回） |

### 特殊字段

| 字段 | 说明 |
|------|------|
| `AutoUUIDField()` | UUID 主键字段，自动生成 |
| `DefaultCodeField()` | 自动编号字段，格式：`前缀+年月日时分+随机数` |
| `DescriptionField()` | 描述字段，默认 `blank=True` |
| `UserForeignKeyField()` | 指向 `AUTH_USER_MODEL` 的外键 |

### 关系字段（无数据库约束）

| 字段 | 说明 |
|------|------|
| `VirtualForeignKey` | 虚拟外键（`db_constraint=False`） |
| `OneToOneField` | 一对一字段（`db_constraint=False`） |
| `VirtualManyToMany` | 虚拟多对多（`db_constraint=False`） |

### PostgreSQL 数组字段

| 字段 | 说明 |
|------|------|
| `ArrayField` | PostgreSQL 数组字段 |
| `ChoiceArrayField` | 选择数组字段，Admin 中显示为多选 |

---

## 抽象模型基类 (models)

`drfexts.models` 提供多种开箱即用的抽象模型基类，所有模型都内置 `StatusQuerySet` 管理器。

### 可用模型基类

| 模型 | 包含字段 | 适用场景 |
|------|---------|---------|
| `BaseModel` | status, updated_at, created_at | 通用基础模型 |
| `BaseCodeModel` | code, status, updated_at, created_at | 需要编号的模型 |
| `BaseCreatorModel` | status, created_by, updated_by, updated_at, created_at | 需要审计人员的模型 |
| `SimpleBaseModel` | status(二态), updated_at, created_at | 简单状态模型 |
| `SimpleBaseCodeModel` | code, status(二态), updated_at, created_at | 简单状态+编号 |
| `SimpleBaseCreatorModel` | status(二态), created_by, updated_by, updated_at, created_at | 简单状态+审计 |
| `UUIDModel` | id(UUID), status, updated_at, created_at | UUID 主键模型 |
| `AuditModel` | status, audit_status, created_by, updated_by, updated_at, created_at | 审核流程模型 |

### 使用示例

```python
from drfexts.models import BaseCreatorModel
from drfexts.fields import CharField, DecimalField

class Product(BaseCreatorModel):
    name = CharField("商品名称", max_length=128)
    price = DecimalField("价格", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "商品"
        verbose_name_plural = verbose_name
```

这会自动拥有 `status`, `created_by`, `updated_by`, `updated_at`, `created_at` 字段。

### StatusQuerySet

所有基类模型自带 `StatusQuerySet` 管理器，提供便捷查询方法：

```python
Product.objects.editable()   # 排除已删除和已失效
Product.objects.active()     # 已生效 + 暂停中 + 待失效
Product.objects.valid()      # 仅已生效
```

### 序列化工具

避免 N+1 查询问题的模型序列化方法：

```python
from drfexts.models import serialize_model, serialize_queryset

qs = Product.objects.select_related("category").prefetch_related("tags")
data = serialize_queryset(qs)
```

---

## 状态与选择 (choices)

`drfexts.choices` / `drfexts.constants` 定义了统一的状态枚举：

### SimpleStatus

| 值 | 标签 |
|----|------|
| 50 | 生效中 |
| 100 | 已失效 |

### CommonStatus

| 值 | 标签 |
|----|------|
| 0 | 已删除 |
| 5 | 待提交 |
| 10 | 待生效 |
| 25 | 暂停中 |
| 50 | 已生效 |
| 75 | 待失效 |
| 100 | 已失效 |

### AuditStatus

三级审核状态，每级包含 `待审核`、`通过`、`驳回` 三个状态。

---

## 序列化器 (serializers)

### WCCModelSerializer

基于 `drf-flex-fields` 的模型序列化器，默认使用 `ComplexPKRelatedField` 处理关联字段。

```python
from drfexts.serializers.serializers import WCCModelSerializer

class ProductSerializer(WCCModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
```

### ComplexPKRelatedField

增强的 PK 关联字段，序列化时返回 `{id: ..., label: ...}` 格式，反序列化时支持直接传 ID 或 `{id: ...}` 格式。

```python
from drfexts.serializers.fields import ComplexPKRelatedField

class OrderSerializer(serializers.ModelSerializer):
    product = ComplexPKRelatedField(
        queryset=Product.objects.all(),
        display_field="name",
    )
```

输出格式：

```json
{
    "product": {
        "id": 1,
        "label": "商品A"
    }
}
```

输入支持：`1` 或 `{"id": 1}` 均可。

### DisplayChoiceField

序列化时显示选择的文字标签，反序列化时接受文字标签转回实际值。

```python
from drfexts.serializers.fields import DisplayChoiceField

status = DisplayChoiceField(choices=CommonStatus.choices)
# 序列化：50 → "已生效"
# 反序列化："已生效" → 50
```

### 其他序列化器字段

| 字段 | 说明 |
|------|------|
| `SequenceField(start=1)` | 只读自增序号字段 |
| `MultiSlugRelatedField(slug_fields=[...])` | 多字段唯一标识的关联字段 |
| `StringListField` | 字符串列表字段 |
| `IntegerListField` | 整数列表字段 |
| `IsNullField` | 判断值是否为 None（只读） |
| `IsNotNullField` | 判断值是否不为 None（只读） |

### DynamicFieldsSerializer

通过 `fields` 参数动态控制返回字段：

```python
serializer = ProductSerializer(instance, fields=["id", "name", "price"])
```

### ExportSerializerMixin

导出序列化器混入，支持通过请求参数 `fields` 和 `fields_map` 控制导出字段和列名映射。自动处理选择字段、布尔字段、关联字段的值翻译。

---

## 视图集 (viewsets)

### ExtGenericViewSet

扩展的通用视图集，提供三项增强：

#### 1. 按 action 指定不同序列化器

```python
from drfexts.viewsets import ExtGenericViewSet
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin

class ProductViewSet(ListModelMixin, RetrieveModelMixin, ExtGenericViewSet):
    queryset = Product.objects.all()
    serializer_class = {
        "default": ProductListSerializer,
        "retrieve": ProductDetailSerializer,
    }
```

#### 2. 动态字段控制

序列化器类可定义 `get_included_fields` / `get_excluded_fields` 类方法，由视图集自动调用：

```python
class ProductSerializer(WCCModelSerializer):
    @classmethod
    def get_included_fields(cls, view, request):
        if request.query_params.get("simple"):
            return ["id", "name"]
        return None
```

#### 3. 查询集优化

序列化器可定义 `process_queryset` 类方法，在 `get_queryset` 时自动调用：

```python
class ProductSerializer(WCCModelSerializer):
    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("category")
```

### EagerLoadingMixin

调用序列化器的 `setup_eager_loading` 方法优化查询：

```python
class ProductViewSet(EagerLoadingMixin, ModelViewSet):
    ...

class ProductSerializer(ModelSerializer):
    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related("category").prefetch_related("tags")
```

### SelectOnlyMixin

自动根据序列化器字段生成 `queryset.only(...)` 查询优化。可通过序列化器 `Meta` 中的 `only_fields`、`expand_only_fields`、`exclude_only_fields` 控制。

### ExportMixin

为视图集添加 CSV/XLSX 导出能力。详见 [数据导出](#数据导出-export) 章节。

---

## 自动过滤器 (filtersets)

### AutoFilterBackend

**核心特性**：根据序列化器字段自动生成过滤器集，无需手动编写 `filterset_class` 或 `filterset_fields`。

```python
from drfexts.filtersets.backends import AutoFilterBackend, OrderingFilterBackend

REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": [
        "drfexts.filtersets.backends.AutoFilterBackend",
        "drfexts.filtersets.backends.OrderingFilterBackend",
    ],
}
```

自动映射规则：

| 序列化器字段 | 自动生成的过滤器 | 支持的查询方式 |
|-------------|-----------------|---------------|
| IntegerField / DecimalField / FloatField | `ExtendedNumberFilter` | 精确值、范围（`field_min`, `field_max`） |
| DateField / DateTimeField | `ExtendedDateFromToRangeFilter` | 日期范围（`field_after`, `field_before`） |
| CharField | `ExtendedCharFilter` | 精确匹配、支持 `value:lookup_expr` 语法 |
| ChoiceField | `ExtendedMultipleChoiceFilter` | 多选（数组、逗号分隔） |
| DisplayChoiceField | `ExtendedDisplayMultipleChoiceFilter` | 多选（按显示值过滤） |
| PrimaryKeyRelatedField | `ExtendedModelMultipleChoiceFilter` | 多选关联查询 |
| BooleanField | `BooleanFilter` | true/false |
| IsNullField / IsNotNullField | `IsNullFilter` / `IsNotNullFilter` | 字段是否为空 |

#### 自定义过滤器覆盖

通过视图的 `filterset_fields_overwrite` 属性覆盖自动生成的过滤器：

```python
class ProductViewSet(ModelViewSet):
    filterset_fields_overwrite = {
        "name": {"lookup_expr": "icontains"},
        "custom_filter": SomeCustomFilter(field_name="..."),
    }
```

### OrderingFilterBackend

支持按序列化器字段名排序，自动将序列化器字段名转换为模型字段名：

```
GET /api/products/?ordering=-price,name
```

### FullTextSearchFilter

PostgreSQL 全文搜索过滤器：

```python
class ProductSearchFilter(FullTextSearchFilter):
    search_vector = ["name", "description"]
```

### 其他过滤器

| 过滤器 | 说明 |
|--------|------|
| `SearchFilter` | 多字段 OR 查询 |
| `MultipleValueFilter` | 多值查询（支持数组、CSV、重复参数） |
| `MultiSearchFilter` | 多字段 OR 搜索 |
| `IsNullFilter` / `IsNotNullFilter` | NULL 值过滤 |
| `ExtendedRangeFilterMixin` | 范围过滤混入 |
| `DataPermissionFilter` | 数据权限过滤 |

---

## 分页 (pagination)

### CustomPagination

默认分页器，支持 `page=all` 返回全部数据。

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "drfexts.pagination.CustomPagination",
    "PAGE_SIZE": 20,
}
```

响应格式：

```json
{
    "total": 100,
    "page_size": 20,
    "current_page": 1,
    "results": [...]
}
```

查询参数：
- `page` — 页码（传 `all` 返回全部数据）
- `page_size` — 每页条数

### WithoutCountPagination

不计算总数的分页，适用于大数据量场景，返回 `previous`/`next` 链接。

### BigPagePagination

大页面分页，默认每页 5000 条，适用于导出等场景。

### CursorSetPagination

游标分页，适用于实时数据流，按 `created_at` 倒序。

---

## 渲染器 (renderers)

### CustomJSONRenderer

基于 `orjson` 的高性能 JSON 渲染器，统一响应格式：

```json
{
    "ret": 200,
    "msg": "success",
    "data": { ... }
}
```

错误时：

```json
{
    "ret": 400,
    "msg": "错误信息",
    "request_id": "..."
}
```

所有 HTTP 响应状态码统一返回 200，实际状态码放在 `ret` 字段中。

配置：

```python
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "drfexts.renderers.CustomJSONRenderer",
    ],
}
```

支持通过 `ORJSON_RENDERER_OPTIONS` 配置 orjson 选项。

### CustomCSVRenderer / CustomXLSXRenderer

CSV（GBK 编码，兼容 Excel 打开）和 XLSX 导出渲染器。由 `ExportMixin` 自动集成。

---

## 解析器 (parsers)

### CustomJSONParser

基于 `orjson` 的高性能 JSON 解析器。

### CustomXLSXParser

Excel (.xlsx) 文件解析器，支持上传 Excel 文件。

### CustomCSVParser

CSV 文件解析器，支持上传 CSV 文件。

```python
REST_FRAMEWORK = {
    "DEFAULT_PARSER_CLASSES": [
        "drfexts.parsers.CustomJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}
```

---

## 数据导出 (export)

通过 `ExportMixin` 为视图集添加 CSV/XLSX 导出能力：

```python
from drfexts.viewsets import ExportMixin
from rest_framework.viewsets import ModelViewSet

class ProductViewSet(ExportMixin, ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    default_base_filename = "products"
```

使用方式：

```
# 导出 CSV
GET /api/products/?format=csv

# 导出 XLSX
GET /api/products/?format=xlsx

# 指定导出文件名
GET /api/products/?format=xlsx&filename=商品列表.xlsx

# 指定导出字段及列名映射
GET /api/products/?format=csv&fields=name,price&fields_map={"name":"商品名","price":"价格"}
```

导出时自动处理：
- 选择字段（ChoiceField）→ 显示文字标签
- 布尔字段 → 显示 "是" / "否"
- 关联字段（ComplexPKRelatedField）→ 显示 label
- 中文文件名 → RFC 5987 编码

---

## 认证 (authentication)

### CsrfExemptSessionAuthentication

免 CSRF 校验的会话认证，适用于前后端分离场景：

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "drfexts.authentication.CsrfExemptSessionAuthentication",
    ],
}
```

---

## 异常处理 (exceptions)

### custom_exception_handler

统一异常处理器，捕获所有异常并返回统一格式。DEBUG 模式下包含堆栈信息。

```python
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "drfexts.exceptions.custom_exception_handler",
}
```

---

## 路由 (routers)

### OptionalSlashRouter

支持 URL 尾部可选斜杠的路由器：

```python
from drfexts.routers import OptionalSlashRouter

router = OptionalSlashRouter()
router.register("products", ProductViewSet)
```

注册的 URL 同时匹配 `/api/products` 和 `/api/products/`。

---

## 存储后端 (storages)

阿里云 OSS 存储后端（基于 `django-storages` 的 S3 兼容层）：

```python
# settings.py
DEFAULT_FILE_STORAGE = "drfexts.storages.AliOSSMediaStorage"
STATICFILES_STORAGE = "drfexts.storages.AliOSSStaticStorage"
```

---

## 工具函数 (utils)

| 函数/类 | 说明 |
|---------|------|
| `get_serial_code(prefix)` | 生成序列号（前缀+年月日时分+随机数） |
| `to_table_choices(choices)` | 将 Django choices 转为前端 `[{label, value}]` 格式 |
| `get_field_info(serializer)` | 提取序列化器字段信息（字段名、标签、选择项等） |
| `get_serializer_field(serializer, field_path)` | 获取序列化器中的字段（支持 `.` 分隔嵌套路径） |
| `atomic_call(func, *args)` | 在数据库事务中执行函数 |
| `strtobool(val)` | 字符串转布尔值 |
| `CustomEncoder` | JSON 编码器（处理 datetime 等类型） |
| `MakeFileHandler(filename)` | 自动创建目录的日志文件处理器 |

---

## 推荐配置

以下是一个完整的 `REST_FRAMEWORK` 配置示例：

```python
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "drfexts.renderers.CustomJSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "drfexts.parsers.CustomJSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "drfexts.pagination.CustomPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "drfexts.filtersets.backends.AutoFilterBackend",
        "drfexts.filtersets.backends.OrderingFilterBackend",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "drfexts.authentication.CsrfExemptSessionAuthentication",
    ],
    "EXCEPTION_HANDLER": "drfexts.exceptions.custom_exception_handler",
}
```

---

## 快速开始示例

```python
# models.py
from drfexts.models import BaseCreatorModel
from drfexts.fields import CharField, DecimalField, VirtualForeignKey

class Category(BaseCreatorModel):
    name = CharField("分类名称", max_length=64)

    class Meta:
        verbose_name = "分类"

class Product(BaseCreatorModel):
    name = CharField("商品名称", max_length=128)
    price = DecimalField("价格", max_digits=10, decimal_places=2)
    category = VirtualForeignKey(Category, verbose_name="分类")

    class Meta:
        verbose_name = "商品"


# serializers.py
from drfexts.serializers.serializers import WCCModelSerializer

class ProductSerializer(WCCModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    @classmethod
    def process_queryset(cls, request, queryset):
        return queryset.select_related("category")


# views.py
from drfexts.viewsets import ExtGenericViewSet, ExportMixin
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin

class ProductViewSet(ExportMixin, ListModelMixin, RetrieveModelMixin, CreateModelMixin, UpdateModelMixin, ExtGenericViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# urls.py
from drfexts.routers import OptionalSlashRouter

router = OptionalSlashRouter()
router.register("products", ProductViewSet)
urlpatterns = router.urls
```

这就是一个完整的 CRUD + 自动过滤 + 排序 + 分页 + CSV/XLSX 导出 的 API，无需额外编写过滤器代码。

---

## License

[Apache-2.0](LICENSE)
