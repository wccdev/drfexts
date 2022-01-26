import copy
from enum import Enum
from typing import Optional, List, Union, Any, Dict
from pydantic import BaseModel


class TypeEnum(str, Enum):
    """
    列类型
    """
    seq = 'seq'
    checkbox = 'checkbox'
    radio = 'radio'
    expand = 'expand'
    html = 'html'


class FixedEnum(str, Enum):
    """
    列固定
    """
    left = 'left'  # 固定左侧
    right = 'right'  # 固定右侧


class AlignEnum(str, Enum):
    """
    对齐方式
    """
    left = 'left'
    center = 'center'
    right = 'right'


class OverflowEnum(str, Enum):
    """
    内容过长时展示行为
    """
    ellipsis = 'ellipsis'  # 只显示省略号
    title = 'title'  # 并且显示为原生
    tooltip = 'tooltip'  # 并且显示为提示


class FieldTypeEnum(str, Enum):
    """
    字段类型
    """
    auto = 'auto'
    number = 'number'
    string = 'string'


class Filter(BaseModel):
    """
    过滤器配置项
    """
    label: str  # 显示的值
    value: Any  # 实际的值
    checked: bool = False  # 默认是否选中
    resetValue: Optional[Any]  # 重置时的默认值
    data: Optional[Any]  # 自定义渲染的数据值（当使用自定义模板时可能会用到）


class CellRender(BaseModel):
    """
    默认的渲染器配置项
    """
    name: str  # 渲染器名称
    props: Any  # 渲染的参数（请查看目标渲染的 Props）
    options: List[Any]  # 只对 name=select 有效，下拉选项列表
    optionProps: Optional[Any]  # 只对 name=select 有效，下拉选项属性参数配置
    optionGroups: List[Any]  # 只对 name=select 有效，下拉分组选项列表
    optionGroupProps: Optional[Any]  # 只对 name=select 有效，下拉分组选项属性参数配置
    events: Optional[Any]
    content: Optional[str]


class EditRender(BaseModel):
    """
    可编辑渲染器配置项
    """
    name: str  # 渲染器名称
    enabled: bool = True  # 是否启用
    props: Optional[Any]  # 渲染的参数（请查看目标渲染的 Props）
    options: Optional[List]  # 只对 name=select 有效，下拉选项列表
    optionProps: Optional[Any]  # 只对 name=select 有效，下拉选项属性参数配置
    optionGroups: Optional[List]  # 只对 name=select 有效，下拉分组选项列表
    optionGroupProps: Optional[Any]  # 只对 name=select 有效，下拉分组选项属性参数配置
    events: Optional[Any]
    content: Optional[str]  # 渲染组件的内容（仅用于特殊组件）
    autofocus: Optional[str]  # 如果是自定义渲染可以指定聚焦的选择器，例如 .my-input
    autoselect: bool = False  # 是否在激活编辑之后自动选中输入框内容
    defaultValue: Optional[Any] = None
    immediate: bool = False  # 输入值实时同步更新（默认情况下单元格编辑的值只会在被触发时同步，如果需要实时同步可以设置为 true）
    placeholder: Optional[str]  # 单元格占位符，但单元格为空值时显示的占位符


class ContentRender(BaseModel):
    """
    内容渲染配置项
    """
    name: str  # 渲染器名称
    props: Optional[Any]  # 渲染的参数（请查看目标渲染的 Props）
    events: Optional[Any]


class Style(BaseModel):
    """
    Properties of Vue-Table-Column.
    """
    type: Optional[TypeEnum]  # 列的类型
    field: Optional[str]  # 列字段名（注：属性层级越深，渲染性能就越差，例如：aa.bb.cc.dd.ee）
    title: Optional[str]  # 列标题（支持开启国际化）
    width: Union[int, str, None]  # 列宽度（如果为空则均匀分配剩余宽度，如果全部列固定了，可能会存在宽屏下不会铺满，可以配合 &quot;%&quot; 或者 &quot;min-width&quot; 布局）
    minWidth: Union[int, str, None]  # 最小列宽度；会自动将剩余空间按比例分配
    resizable: Optional[bool]  # 列是否允许拖动列宽调整大小
    visible: bool = True  # 默认是否显示
    fixed: Optional[FixedEnum]  # 将列固定在左侧或者右侧（注意：固定列应该放在左右两侧的位置）
    align: Optional[AlignEnum]  # 列对齐方式
    headerAlign: Optional[AlignEnum]  # 表头列对齐方式
    footerAlign: Optional[AlignEnum]  # 表尾列对齐方式
    showOverflow: Optional[OverflowEnum]  # 内容过长时显示为省略号
    showHeaderOverflow: Optional[OverflowEnum]  # 当表头内容过长时显示为省略号
    showFooterOverflow: Optional[OverflowEnum]  # 当表尾内容过长时显示为省略号
    className: Optional[str]  # 给单元格附加 className
    headerClassName: Optional[str]  # 给表头的单元格附加 className
    footerClassName: Optional[str]  # 给表尾的单元格附加 className
    formatter: Optional[Any]  # 格式化显示内容
    sortable: bool = False  # 是否允许排序
    sortBy: Optional[str]  # 只对 sortable 有效，指定排序的字段（当值 formatter 格式化后，可以设置该字段，使用值进行排序）
    sortType: FieldTypeEnum = FieldTypeEnum.auto  # 排序的字段类型，比如字符串转数值等
    filters: Optional[List[Filter]]  # 配置筛选条件（注：筛选只能用于列表，如果是树结构则过滤根节点）
    filterMultiple: bool = True  # 只对 filters 有效，筛选是否允许多选
    filterMethod: Optional[Any]  # 只对 filters 有效，列的筛选方法，该方法的返回值用来决定该行是否显示
    cellType: FieldTypeEnum = FieldTypeEnum.auto  # 只对特定功能有效，单元格值类型（例如：导出数据类型设置）
    cellRender: Optional[CellRender]  # 默认的渲染器配置项
    editRender: Optional[EditRender]  # 可编辑渲染器配置项
    contentRender: Optional[ContentRender]  # 内容渲染器配置项
    treeNode: bool = False  # 只对 tree-config 配置时有效，指定为树节点
    params: Optional[Any]  # 额外的参数（可以用来存放一些私有参数）
    children: Optional[List]  # 表头分组



