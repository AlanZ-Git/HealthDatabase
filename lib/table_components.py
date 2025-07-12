"""
表格组件模块
包含与表格相关的高级组件和管理器，提供可复用的表格功能
"""

from PyQt6.QtWidgets import QHeaderView, QTableWidget, QHBoxLayout, QLineEdit
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Optional, List, Callable, Any


# ==================== 通用工具函数 ====================

def multi_keyword_search(text: str, keywords: str) -> bool:
    """
    多关键字搜索函数 - 从table_viewer.py抽象而来
    
    Args:
        text: 要搜索的文本内容
        keywords: 搜索关键字，用空格分隔多个关键字
        
    Returns:
        如果文本包含所有关键字则返回True，否则返回False
    """
    if not keywords.strip():
        return True  # 空搜索匹配所有内容
    
    if not text:
        return False  # 空文本不匹配任何关键字
    
    # 将搜索关键字按空格分割，并去掉空字符串
    keyword_list = [kw.strip().lower() for kw in keywords.split() if kw.strip()]
    
    if not keyword_list:
        return True  # 没有有效关键字，匹配所有内容
    
    # 将文本转换为小写进行不区分大小写的搜索
    text_lower = text.lower()
    
    # 检查是否所有关键字都在文本中出现
    for keyword in keyword_list:
        if keyword not in text_lower:
            return False
    
    return True


def filter_records_by_search(records: List[Dict], search_text: str, field_names: List[str]) -> List[Dict]:
    """
    根据搜索文本过滤记录 - 从table_viewer.py抽象并通用化
    
    Args:
        records: 原始记录列表
        search_text: 搜索文本
        field_names: 要搜索的字段名列表
        
    Returns:
        过滤后的记录列表
    """
    if not search_text.strip():
        return records  # 空搜索返回所有记录
    
    filtered = []
    
    for record in records:
        # 将记录中指定字段的内容连接起来进行搜索
        searchable_text = " ".join([
            str(record.get(field, '')) for field in field_names
        ])
        
        # 使用多关键字搜索函数
        if multi_keyword_search(searchable_text, search_text):
            filtered.append(record)
    
    return filtered


# ==================== 列宽管理器 ====================

class GenericColumnWidthManager(QObject):
    """
    通用表格列宽管理器 - 从column_width_manager.py改进而来
    支持固定像素列和比例列的混合布局，适用于任何需要灵活列宽管理的表格
    
    使用示例:
        # 简单使用
        manager = GenericColumnWidthManager(
            table_widget=my_table,
            fixed_columns=[0, 1],  # 前两列固定宽度
            proportional_columns=[2, 3, 4]  # 后三列按比例分配
        )
        
        # 高级使用
        manager = GenericColumnWidthManager(
            table_widget=my_table,
            fixed_columns=[0, 1], 
            proportional_columns=[2, 3, 4],
            default_fixed_widths={0: 50, 1: 80},
            default_proportional_ratios={2: 0.4, 3: 0.4, 4: 0.2},
            config_loader=load_my_config,
            config_saver=save_my_config
        )
    """
    
    column_width_changed = pyqtSignal(int, int, int)  # logical_index, old_size, new_size
    
    def __init__(self, 
                 table_widget: QTableWidget,
                 fixed_columns: List[int] = None,
                 proportional_columns: List[int] = None,
                 default_fixed_widths: Dict[int, int] = None,
                 default_proportional_ratios: Dict[int, float] = None,
                 config_loader: Optional[Callable] = None,
                 config_saver: Optional[Callable] = None,
                 min_column_width: int = 30):
        """
        初始化通用列宽管理器
        
        Args:
            table_widget: 需要管理列宽的表格控件
            fixed_columns: 固定像素列的索引列表
            proportional_columns: 比例列的索引列表  
            default_fixed_widths: 默认固定列宽度字典 {列索引: 像素宽度}
            default_proportional_ratios: 默认比例列比例字典 {列索引: 比例值}
            config_loader: 配置加载回调函数，返回 (fixed_widths, proportional_ratios)
            config_saver: 配置保存回调函数，接收 (fixed_widths, proportional_ratios)
            min_column_width: 列的最小宽度（像素）
        """
        super().__init__()
        self.table = table_widget
        self.min_column_width = min_column_width
        
        # 列分类配置
        self.fixed_columns = fixed_columns or []
        self.proportional_columns = proportional_columns or []
        self.total_columns = max(
            max(self.fixed_columns) if self.fixed_columns else 0,
            max(self.proportional_columns) if self.proportional_columns else 0
        ) + 1
        
        # 默认配置
        self.default_fixed_widths = default_fixed_widths or {}
        self.default_proportional_ratios = default_proportional_ratios or {}
        
        # 配置持久化回调
        self.config_loader = config_loader
        self.config_saver = config_saver
        
        # 运行时数据
        self.fixed_column_widths = {}
        self.proportional_column_ratios = {}
        self.is_adjusting_columns = False
        
        # 初始化
        self.load_settings()
    
    def load_settings(self):
        """加载列宽设置"""
        if self.config_loader:
            try:
                self.fixed_column_widths, self.proportional_column_ratios = self.config_loader()
                self._validate_and_normalize_settings()
                return
            except Exception:
                pass
        
        # 使用默认配置
        self._load_default_settings()
    
    def _load_default_settings(self):
        """加载默认设置"""
        self.fixed_column_widths = self.default_fixed_widths.copy()
        self.proportional_column_ratios = self.default_proportional_ratios.copy()
        
        # 为未配置的列设置默认值
        for col in self.fixed_columns:
            if col not in self.fixed_column_widths:
                self.fixed_column_widths[col] = 80
        
        num_proportional = len(self.proportional_columns)
        if num_proportional > 0:
            for col in self.proportional_columns:
                if col not in self.proportional_column_ratios:
                    self.proportional_column_ratios[col] = 1.0 / num_proportional
        
        self._normalize_proportional_ratios()
    
    def _validate_and_normalize_settings(self):
        """验证并归一化设置"""
        # 确保所有固定列都有宽度配置
        for col in self.fixed_columns:
            if col not in self.fixed_column_widths:
                self.fixed_column_widths[col] = 80
        
        # 确保所有比例列都有比例配置
        for col in self.proportional_columns:
            if col not in self.proportional_column_ratios:
                self.proportional_column_ratios[col] = 0.1
        
        self._normalize_proportional_ratios()
    
    def _normalize_proportional_ratios(self):
        """归一化比例值，确保总和为1.0"""
        if not self.proportional_column_ratios:
            return
            
        total = sum(self.proportional_column_ratios.values())
        if total > 0:
            for col in self.proportional_column_ratios:
                self.proportional_column_ratios[col] /= total
    
    def save_settings(self):
        """保存列宽设置"""
        if self.config_saver:
            try:
                self.config_saver(self.fixed_column_widths, self.proportional_column_ratios)
            except Exception:
                pass
    
    def save_user_column_widths(self):
        """保存用户自定义列宽设置 - 兼容原ColumnWidthManager接口"""
        if self.is_adjusting_columns:
            return  # 如果正在批量调整列宽，不保存
        
        # 更新固定列宽度
        for col in self.fixed_columns:
            width = self.table.columnWidth(col)
            self.fixed_column_widths[col] = width
        
        # 计算并更新比例列的比例
        total_proportional_width = sum(
            self.table.columnWidth(col) for col in self.proportional_columns
        )
        
        if total_proportional_width > 0:
            for col in self.proportional_columns:
                proportion = self.table.columnWidth(col) / total_proportional_width
                self.proportional_column_ratios[col] = proportion
        
        # 保存配置
        self.save_settings()
    
    def calculate_proportional_widths(self, available_width: Optional[int] = None) -> Dict[int, int]:
        """计算比例列的实际像素宽度"""
        if available_width is None:
            table_width = self.table.width()
            fixed_total_width = sum(self.fixed_column_widths.values())
            scrollbar_width = 20
            available_width = max(200, table_width - fixed_total_width - scrollbar_width)
        
        proportional_widths = {}
        for col in self.proportional_columns:
            ratio = self.proportional_column_ratios.get(col, 1.0 / len(self.proportional_columns))
            width = max(self.min_column_width, int(available_width * ratio))
            proportional_widths[col] = width
        
        return proportional_widths
    
    def apply_widths(self):
        """应用列宽设置到表格"""
        if not hasattr(self.table, 'horizontalHeader'):
            return
            
        self.is_adjusting_columns = True
        
        try:
            header = self.table.horizontalHeader()
            proportional_widths = self.calculate_proportional_widths()
            
            # 设置所有列为可交互模式
            for i in range(self.total_columns):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            
            # 应用固定列宽度
            for col, width in self.fixed_column_widths.items():
                self.table.setColumnWidth(col, max(self.min_column_width, width))
            
            # 应用比例列宽度
            for col, width in proportional_widths.items():
                self.table.setColumnWidth(col, width)
        
        finally:
            self.is_adjusting_columns = False
    
    def on_column_width_changed(self, logical_index: int, old_size: int, new_size: int):
        """列宽改变时的处理函数"""
        if self.is_adjusting_columns:
            return
            
        # 更新配置
        if logical_index in self.fixed_columns:
            self.fixed_column_widths[logical_index] = new_size
        elif logical_index in self.proportional_columns:
            # 重新计算所有比例列的比例
            self._recalculate_proportional_ratios()
            # 立即重新应用比例列宽度，确保比例列之间的宽度关系保持一致
            self._apply_proportional_widths_only()
        
        # 保存配置
        self.save_settings()
        
        # 发出信号
        self.column_width_changed.emit(logical_index, old_size, new_size)
    
    def _recalculate_proportional_ratios(self):
        """重新计算比例列的比例"""
        total_width = sum(self.table.columnWidth(col) for col in self.proportional_columns)
        if total_width > 0:
            for col in self.proportional_columns:
                self.proportional_column_ratios[col] = self.table.columnWidth(col) / total_width
    
    def _apply_proportional_widths_only(self):
        """只重新应用比例列的宽度，不影响固定列"""
        if not hasattr(self.table, 'horizontalHeader'):
            return
        
        # 设置调整标志，防止递归调用
        self.is_adjusting_columns = True
        
        try:
            # 计算可用宽度：总宽度减去固定列宽度和滚动条宽度
            table_width = self.table.width()
            fixed_total_width = sum(self.fixed_column_widths.values())
            scrollbar_width = 20
            available_width = max(200, table_width - fixed_total_width - scrollbar_width)
            
            # 计算并应用比例列宽度
            proportional_widths = self.calculate_proportional_widths(available_width)
            
            for col, width in proportional_widths.items():
                self.table.setColumnWidth(col, width)
        
        finally:
            self.is_adjusting_columns = False
    
    def handle_resize_event(self):
        """处理窗口大小改变事件"""
        if self.table is not None:
            self.apply_widths()
    
    def reset_to_defaults(self):
        """重置为默认列宽"""
        self._load_default_settings()
        self.apply_widths()
        self.save_settings()
    
    def reset_to_default_column_widths(self):
        """重置列宽为默认设置 - 兼容原ColumnWidthManager接口"""
        # 如果有配置加载器，尝试重置配置
        if self.config_loader and hasattr(self, '_config_reset_callback'):
            try:
                self._config_reset_callback()
            except Exception:
                pass
        
        # 重新加载设置并应用
        self.reset_to_defaults()
    
    # 查询方法
    def get_column_width(self, column_index: int) -> int:
        """获取指定列的当前宽度"""
        return self.table.columnWidth(column_index)
    
    def is_fixed_column(self, column_index: int) -> bool:
        """判断指定列是否为固定像素列"""
        return column_index in self.fixed_columns
    
    def is_proportional_column(self, column_index: int) -> bool:
        """判断指定列是否为比例列"""
        return column_index in self.proportional_columns


# ==================== 表格筛选管理器 ====================

class TableFilterManager(QObject):
    """
    表格筛选管理器 - 从table_viewer.py抽象而来
    管理单列筛选功能，支持为每列创建筛选输入框并与表格列宽同步
    """
    
    filter_changed = pyqtSignal(dict)  # 筛选条件改变信号，传递 {列索引: 筛选文本}
    
    def __init__(self, 
                 table_widget: QTableWidget,
                 filter_layout: QHBoxLayout,
                 column_headers: List[str],
                 filterable_columns: List[int] = None):
        """
        初始化筛选管理器
        
        Args:
            table_widget: 表格控件
            filter_layout: 筛选输入框的布局
            column_headers: 列标题列表
            filterable_columns: 可筛选的列索引列表，None表示所有列都可筛选
        """
        super().__init__()
        self.table = table_widget
        self.filter_layout = filter_layout
        self.column_headers = column_headers
        self.filterable_columns = filterable_columns or list(range(len(column_headers)))
        
        self.filter_widgets = []  # 筛选输入框列表
        self.column_filters = {}  # 当前筛选条件 {列索引: 筛选文本}
        self.enabled = False
        
        self.create_filter_widgets()
    
    def create_filter_widgets(self):
        """创建单列筛选输入框"""
        # 清除现有控件
        for widget in self.filter_widgets:
            widget.deleteLater()
        self.filter_widgets.clear()
        
        # 为每一列创建筛选输入框
        for i, header in enumerate(self.column_headers):
            filter_input = QLineEdit()
            
            if i in self.filterable_columns:
                filter_input.setPlaceholderText(f"筛选{header}")
                filter_input.textChanged.connect(lambda text, col=i: self.on_filter_changed(col, text))
            else:
                filter_input.setEnabled(False)
                filter_input.setPlaceholderText("")
            
            self.filter_widgets.append(filter_input)
            self.filter_layout.addWidget(filter_input)
        
        self.update_widget_sizes()
    
    def update_widget_sizes(self):
        """更新筛选输入框的宽度以匹配表格列宽"""
        if not self.enabled or not self.filter_widgets:
            return
        
        # 设置布局属性
        self.filter_layout.setSpacing(0)
        frame_width = self.table.frameWidth()
        self.filter_layout.setContentsMargins(frame_width, 0, frame_width, 0)
        
        # 更新每个输入框的宽度
        for i, filter_input in enumerate(self.filter_widgets):
            column_width = self.table.columnWidth(i)
            filter_input.setFixedWidth(column_width)
            filter_input.setMinimumWidth(column_width)
            filter_input.setMaximumWidth(column_width)
            
            # 设置样式
            filter_input.setStyleSheet("""
                QLineEdit { 
                    border: 1px solid #ccc; 
                    margin: 0px; 
                    padding: 1px 2px;
                    border-radius: 0px;
                    background-color: white;
                }
                QLineEdit:focus {
                    border: 2px solid #0078d4;
                }
            """)
    
    def on_filter_changed(self, column_index: int, text: str):
        """筛选文本改变处理"""
        if text.strip():
            self.column_filters[column_index] = text.strip()
        else:
            if column_index in self.column_filters:
                del self.column_filters[column_index]
        
        self.filter_changed.emit(self.column_filters.copy())
    
    def set_enabled(self, enabled: bool):
        """启用或禁用筛选功能"""
        self.enabled = enabled
        
        if enabled:
            self.update_widget_sizes()
        else:
            # 清除所有筛选条件
            self.column_filters.clear()
            for filter_input in self.filter_widgets:
                filter_input.clear()
            self.filter_changed.emit({})
    
    def clear_all_filters(self):
        """清除所有筛选条件"""
        self.column_filters.clear()
        for filter_input in self.filter_widgets:
            filter_input.clear()
        self.filter_changed.emit({})
    
    def filter_records(self, records: List[Dict], field_mapping: Dict[int, str]) -> List[Dict]:
        """
        根据筛选条件过滤记录
        
        Args:
            records: 原始记录列表
            field_mapping: 列索引到字段名的映射 {列索引: 字段名}
            
        Returns:
            过滤后的记录列表
        """
        if not self.column_filters:
            return records
        
        filtered = []
        
        for record in records:
            match_all_filters = True
            
            for column_index, filter_text in self.column_filters.items():
                field_name = field_mapping.get(column_index)
                if not field_name:
                    continue
                
                field_value = str(record.get(field_name, ''))
                
                if not multi_keyword_search(field_value, filter_text):
                    match_all_filters = False
                    break
            
            if match_all_filters:
                filtered.append(record)
        
        return filtered


# ==================== 表格排序管理器 ====================

class TableSortManager(QObject):
    """
    表格排序管理器 - 从table_viewer.py抽象而来
    管理表格列的排序功能，支持点击表头进行排序
    """
    
    sort_changed = pyqtSignal(str, str)  # 排序改变信号: (字段名, 排序方向ASC/DESC)
    
    def __init__(self, 
                 table_widget: QTableWidget,
                 sortable_columns: Dict[int, str],
                 default_sort_field: str = None,
                 default_sort_order: str = 'ASC'):
        """
        初始化排序管理器
        
        Args:
            table_widget: 表格控件
            sortable_columns: 可排序的列 {列索引: 字段名}
            default_sort_field: 默认排序字段
            default_sort_order: 默认排序方向 ('ASC' 或 'DESC')
        """
        super().__init__()
        self.table = table_widget
        self.sortable_columns = sortable_columns
        self.current_sort_field = default_sort_field or list(sortable_columns.values())[0]
        self.current_sort_order = default_sort_order
        self.base_headers = []
        
        # 连接表头点击信号
        header = self.table.horizontalHeader()
        header.sectionClicked.connect(self.on_header_clicked)
    
    def set_headers(self, headers: List[str]):
        """设置基础表头"""
        self.base_headers = headers.copy()
        self.update_header_display()
    
    def on_header_clicked(self, logical_index: int):
        """表格标题点击事件处理"""
        if logical_index not in self.sortable_columns:
            return
        
        clicked_field = self.sortable_columns[logical_index]
        
        # 切换排序
        if clicked_field == self.current_sort_field:
            self.current_sort_order = 'DESC' if self.current_sort_order == 'ASC' else 'ASC'
        else:
            self.current_sort_field = clicked_field
            self.current_sort_order = 'ASC'
        
        self.update_header_display()
        self.sort_changed.emit(self.current_sort_field, self.current_sort_order)
    
    def update_header_display(self):
        """更新表格标题，显示排序指示器"""
        if not self.base_headers:
            return
        
        updated_headers = self.base_headers.copy()
        
        # 为当前排序列添加排序指示器
        for col_index, field_name in self.sortable_columns.items():
            if field_name == self.current_sort_field:
                indicator = " ▲" if self.current_sort_order == 'ASC' else " ▼"
                if col_index < len(updated_headers):
                    updated_headers[col_index] = self.base_headers[col_index] + indicator
        
        self.table.setHorizontalHeaderLabels(updated_headers)
    
    def get_current_sort(self) -> tuple[str, str]:
        """获取当前排序设置"""
        return self.current_sort_field, self.current_sort_order
    
    def set_sort(self, field: str, order: str):
        """设置排序"""
        if field in self.sortable_columns.values() and order in ['ASC', 'DESC']:
            self.current_sort_field = field
            self.current_sort_order = order
            self.update_header_display()


# ==================== 便捷工厂函数 ====================

def create_health_db_column_manager(table_widget: QTableWidget, config_manager=None):
    """
    为健康数据库项目创建列宽管理器
    这是一个便捷函数，封装了健康数据库特定的列配置，完全兼容原ColumnWidthManager
    """
    try:
        from .config_manager import ConfigManager
    except ImportError:
        raise ImportError("需要ConfigManager来创建健康数据库列宽管理器")
    
    if config_manager is None:
        config_manager = ConfigManager()
    
    manager = GenericColumnWidthManager(
        table_widget=table_widget,
        fixed_columns=[0, 1, 2, 5, 6, 11],
        proportional_columns=[3, 4, 7, 8, 9, 10],
        default_fixed_widths={0: 50, 1: 55, 2: 93, 5: 61, 6: 102, 11: 80},
        default_proportional_ratios={3: 0.20, 4: 0.15, 7: 0.25, 8: 0.20, 9: 0.12, 10: 0.08},
        config_loader=lambda: config_manager.get_column_widths(),
        config_saver=lambda fw, pr: config_manager.save_column_widths(fw, pr)
    )
    
    # 添加配置重置回调，确保完全兼容原ColumnWidthManager
    manager._config_reset_callback = lambda: config_manager.reset_column_widths()
    
    return manager


def create_health_db_filter_manager(table_widget: QTableWidget, filter_layout: QHBoxLayout):
    """为健康数据库创建筛选管理器"""
    headers = [
        "选择", "记录ID", "就诊日期", "医院", "科室", "医生", 
        "器官系统", "症状事由", "诊断结果", "用药信息", "备注", "附件"
    ]
    filterable_columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 除了选择列和附件列
    
    return TableFilterManager(
        table_widget=table_widget,
        filter_layout=filter_layout,
        column_headers=headers,
        filterable_columns=filterable_columns
    )


def create_health_db_sort_manager(table_widget: QTableWidget):
    """为健康数据库创建排序管理器"""
    sortable_columns = {1: 'visit_record_id', 2: 'date'}
    
    return TableSortManager(
        table_widget=table_widget,
        sortable_columns=sortable_columns,
        default_sort_field='visit_record_id',
        default_sort_order='ASC'
    ) 