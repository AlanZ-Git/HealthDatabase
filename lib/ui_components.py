"""
通用UI组件库
包含可复用的UI组件和混入类，用于减少代码重复
"""

from PyQt6.QtWidgets import (
    QWidget, QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QLineEdit, 
    QListWidget, QListWidgetItem, QCheckBox, QCompleter, QLabel, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import os
from typing import List, Callable, Optional

# 统一的勾选框高亮样式
CHECKBOX_HIGHLIGHT_STYLE = """
QCheckBox { 
    spacing: 5px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #ddd;
    border-radius: 3px;
    background-color: white;
}
QCheckBox::indicator:checked {
    background-color: #104d8f;
    border: 2px solid #0a3f73;
    color: white;
}
QCheckBox::indicator:hover {
    border-color: #0078d4;
}
QCheckBox::indicator:checked:hover {
    background-color: #0a3f73;
    border-color: #083159;
}
"""


class AutoCompleteLineEdit(QLineEdit):
    """自动完成输入框组件"""
    
    def __init__(self, placeholder_text: str = "", history_limit: int = 5, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.history_limit = history_limit
        self.data_fetcher = None
        
        # 创建自动完成器
        self._setup_completer()
        
        # 连接textChanged信号来动态更新自动完成选项
        self.textChanged.connect(self._update_completer)
    
    def _setup_completer(self):
        """设置自动完成器"""
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)  # 支持中间字符匹配
        self.setCompleter(completer)
        
    def set_data_fetcher(self, fetcher_func):
        """设置数据获取函数"""
        self.data_fetcher = fetcher_func
        
    def focusInEvent(self, event):
        """获取焦点时更新补全列表并显示"""
        super().focusInEvent(event)
        self._update_completer()
        
        # 如果输入框为空，主动弹出补全列表显示历史记录
        if not self.text().strip():
            self._show_all_completions()
    
    def _show_all_completions(self):
        """显示所有补全选项"""
        if self.completer() and self.completer().model():
            if self.completer().model().rowCount() > 0:
                # 设置完成前缀为空字符串以显示所有选项
                self.completer().setCompletionPrefix("")
                # 获取输入框的几何位置并弹出补全列表
                rect = self.rect()
                rect.setWidth(self.completer().popup().sizeHintForColumn(0) + 
                             self.completer().popup().verticalScrollBar().sizeHint().width())
                self.completer().complete(rect)
    
    def _update_completer(self):
        """更新自动完成数据"""
        if self.data_fetcher:
            try:
                data = self.data_fetcher(self.history_limit)
                model = QStringListModel(data)
                self.completer().setModel(model)
            except Exception:
                # 忽略数据获取错误
                pass

    def keyPressEvent(self, event):
        """处理键盘事件"""
        # 如果按下向下箭头键且输入框为空，显示所有历史记录
        if (event.key() == Qt.Key.Key_Down and not self.text().strip()):
            self._show_all_completions()
        else:
            super().keyPressEvent(event)


class CheckboxClickHandler:
    """
    统一的勾选框点击处理器
    用于处理"行高亮 vs 勾选状态切换"的逻辑
    """
    
    @staticmethod
    def should_toggle_checkbox(click_position, checkbox_column_or_area=0):
        """
        判断点击是否应该切换勾选状态
        
        Args:
            click_position: 点击位置的索引或区域标识
            checkbox_column_or_area: 勾选框所在的列或区域标识
            
        Returns:
            bool: 是否应该切换勾选状态
        """
        return click_position == checkbox_column_or_area
    
    @staticmethod
    def handle_table_click(index, table_widget, checkbox_column=0):
        """
        处理表格点击事件
        
        Args:
            index: QModelIndex 点击的位置
            table_widget: QTableWidget 表格组件
            checkbox_column: int 勾选框所在的列号（默认第0列）
            
        Returns:
            bool: 是否执行了勾选切换
        """
        if not CheckboxClickHandler.should_toggle_checkbox(index.column(), checkbox_column):
            return False
        
        row = index.row()
        if 0 <= row < table_widget.rowCount():
            checkbox = table_widget.cellWidget(row, checkbox_column)
            if checkbox and hasattr(checkbox, 'setChecked'):
                checkbox.setChecked(not checkbox.isChecked())
                return True
        return False
    
    @staticmethod
    def handle_list_click(item, list_widget, checkbox_area_only=True):
        """
        处理列表点击事件
        
        Args:
            item: QListWidgetItem 点击的项目
            list_widget: QListWidget 列表组件
            checkbox_area_only: bool 是否仅在勾选框区域点击时切换
            
        Returns:
            bool: 是否执行了勾选切换
        """
        if not item:
            return False
        
        checkbox = list_widget.itemWidget(item)
        if checkbox and hasattr(checkbox, 'setChecked'):
            # 如果设置为仅勾选框区域，这里可以进一步细化判断
            # 目前简化处理：如果checkbox_area_only为True，则不切换（需要直接点击勾选框）
            if checkbox_area_only:
                return False
            
            checkbox.setChecked(not checkbox.isChecked())
            return True
        return False


class DragDropMixin:
    """
    拖拽功能混入类，为任何QWidget添加拖拽能力
    减少拖拽代码重复（约85行重复代码）
    """
    
    def enable_drag_drop(self, file_handler: Optional[Callable] = None):
        """
        启用拖拽功能
        
        Args:
            file_handler: 文件处理回调函数，接收文件路径列表
        """
        self.setAcceptDrops(True)
        self.file_handler = file_handler
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """统一的拖拽进入处理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """统一的拖拽放下处理，调用自定义处理函数"""
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    file_paths.append(file_path)
            
            if file_paths and self.file_handler:
                self.file_handler(file_paths)
            
            event.acceptProposedAction()
        else:
            event.ignore()


class StandardButtonBar(QHBoxLayout):
    """
    标准按钮栏组件，支持左对齐、右对齐、居中、拉伸分组
    减少按钮布局重复代码（约120行重复代码）
    """
    
    def __init__(self, spacing: int = 6):
        super().__init__()
        self.setSpacing(spacing)
    
    def add_left_buttons(self, buttons: List[QPushButton]):
        """添加左对齐按钮组"""
        for btn in buttons:
            self.addWidget(btn)
    
    def add_center_buttons(self, buttons: List[QPushButton]):
        """添加居中按钮组"""
        self.addStretch()
        for btn in buttons:
            self.addWidget(btn)
        self.addStretch()
    
    def add_right_buttons(self, buttons: List[QPushButton]):
        """添加右对齐按钮组"""
        if self.count() > 0:  # 如果已经有控件，添加拉伸
            self.addStretch()
        for btn in buttons:
            self.addWidget(btn)
    
    def add_spacing(self, size: int):
        """添加间距"""
        self.addSpacing(size)
    
    def add_stretch(self):
        """添加拉伸"""
        super().addStretch()


class PaginationBar(StandardButtonBar):
    """
    分页按钮栏，整合表格分页逻辑
    """
    
    page_changed = pyqtSignal(int)  # 页码改变信号
    page_size_changed = pyqtSignal(int)  # 每页大小改变信号
    
    def __init__(self, initial_page_size: int = 15):
        super().__init__()
        self.current_page = 1
        self.total_pages = 1
        self.setup_pagination_controls(initial_page_size)
    
    def setup_pagination_controls(self, initial_page_size: int):
        """设置分页控件"""
        # 每页记录数设置
        self.page_size_label = QLabel("每页")
        self.addWidget(self.page_size_label)
        
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setMinimum(1)
        self.page_size_spinbox.setMaximum(1000)
        self.page_size_spinbox.setValue(initial_page_size)
        self.page_size_spinbox.valueChanged.connect(self.on_page_size_changed)
        self.page_size_spinbox.setFixedWidth(60)
        self.addWidget(self.page_size_spinbox)
        
        self.page_size_label2 = QLabel("条记录")
        self.addWidget(self.page_size_label2)
        
        # 分页按钮
        self.add_spacing(20)
        
        self.first_page_btn = QPushButton("首页")
        self.first_page_btn.clicked.connect(lambda: self.go_to_page(1))
        self.first_page_btn.setFixedWidth(60)
        self.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(lambda: self.go_to_page(self.current_page - 1))
        self.prev_page_btn.setFixedWidth(70)
        self.addWidget(self.prev_page_btn)
        
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(lambda: self.go_to_page(self.current_page + 1))
        self.next_page_btn.setFixedWidth(70)
        self.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("末页")
        self.last_page_btn.clicked.connect(lambda: self.go_to_page(self.total_pages))
        self.last_page_btn.setFixedWidth(60)
        self.addWidget(self.last_page_btn)
        
        # 页码信息
        self.page_info_label = QLabel("第1页 / 共1页")
        self.addWidget(self.page_info_label)
    
    def go_to_page(self, page: int):
        """跳转到指定页"""
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.current_page = page
            self.update_button_states()
            self.page_changed.emit(page)
    
    def on_page_size_changed(self, size: int):
        """每页大小改变处理"""
        self.page_size_changed.emit(size)
    
    def update_pagination_info(self, current_page: int, total_pages: int):
        """更新分页信息"""
        self.current_page = current_page
        self.total_pages = total_pages
        self.page_info_label.setText(f"第{current_page}页 / 共{total_pages}页")
        self.update_button_states()
    
    def update_button_states(self):
        """更新按钮状态"""
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)


class CheckableListWidget(QListWidget):
    """
    带复选框的列表组件，支持批量操作
    减少列表管理重复代码（约150行重复代码）
    """
    
    items_changed = pyqtSignal()  # 列表项目改变信号
    selection_changed = pyqtSignal()  # 选择状态改变信号
    
    def __init__(self, empty_placeholder: str = "暂无数据"):
        super().__init__()
        self.empty_placeholder = empty_placeholder
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI样式"""
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #c0c0c0;
                background-color: #ffffff;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #3399ff;
                color: white;
            }
        """)
        # 连接信号
        self.itemClicked.connect(self.on_item_clicked)
    
    def add_checkable_item(self, text: str, data=None, checked: bool = False):
        """添加可勾选项目"""
        item = QListWidgetItem()
        
        # 创建包含勾选框和标签的自定义widget
        item_widget = self._create_checkable_item_widget(text, checked)
        
        # 存储数据
        item.setData(Qt.ItemDataRole.UserRole, data)
        
        self.addItem(item)
        self.setItemWidget(item, item_widget)
        
        self.items_changed.emit()
        self.update_placeholder()
    
    def _create_checkable_item_widget(self, text: str, checked: bool = False):
        """创建包含勾选框和标签的widget"""
        from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
        
        # 创建容器widget
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(8)
        
        # 创建勾选框
        checkbox = QCheckBox()
        checkbox.setChecked(checked)
        checkbox.setStyleSheet(CHECKBOX_HIGHLIGHT_STYLE)
        checkbox.stateChanged.connect(self.on_checkbox_changed)
        layout.addWidget(checkbox)
        
        # 创建文字标签
        label = QLabel(text)
        label.setStyleSheet("QLabel { background: transparent; }")
        layout.addWidget(label)
        
        layout.addStretch()
        
        # 在容器上存储勾选框引用，方便后续访问
        container.checkbox = checkbox
        container.label = label
        
        return container
    
    def get_checked_items(self):
        """获取所有勾选的项目数据"""
        checked_items = []
        for i in range(self.count()):
            item = self.item(i)
            item_widget = self.itemWidget(item)
            if item_widget and hasattr(item_widget, 'checkbox'):
                checkbox = item_widget.checkbox
                if checkbox.isChecked():
                    data = item.data(Qt.ItemDataRole.UserRole)
                    checked_items.append(data)
        return checked_items
    
    def get_checked_indices(self):
        """获取所有勾选的项目索引"""
        checked_indices = []
        for i in range(self.count()):
            item = self.item(i)
            item_widget = self.itemWidget(item)
            if item_widget and hasattr(item_widget, 'checkbox'):
                checkbox = item_widget.checkbox
                if checkbox.isChecked():
                    checked_indices.append(i)
        return checked_indices
    
    def remove_checked_items(self):
        """删除所有勾选的项目"""
        indices_to_remove = self.get_checked_indices()
        
        # 从后往前删除，避免索引变化
        for i in reversed(indices_to_remove):
            self.takeItem(i)
        
        if indices_to_remove:
            self.items_changed.emit()
        
        self.update_placeholder()
    
    def clear_all_items(self):
        """清除所有项目"""
        self.clear()
        self.items_changed.emit()
        self.update_placeholder()
    
    def set_all_checked(self, checked: bool):
        """设置所有项目的勾选状态"""
        for i in range(self.count()):
            item = self.item(i)
            item_widget = self.itemWidget(item)
            if item_widget and hasattr(item_widget, 'checkbox'):
                item_widget.checkbox.setChecked(checked)
    
    def update_placeholder(self):
        """更新占位符显示"""
        if self.count() == 0:
            placeholder_item = QListWidgetItem(self.empty_placeholder)
            placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder_item.setForeground(Qt.GlobalColor.gray)
            self.addItem(placeholder_item)
    
    def on_item_clicked(self, item):
        """项目点击处理（仅在勾选框区域点击时切换勾选状态）"""
        # 新的布局结构下，点击列表项本身不应该切换勾选状态
        # 只有直接点击勾选框才会切换状态，这已经通过勾选框的信号处理了
        pass
    
    def on_checkbox_changed(self):
        """复选框状态改变处理"""
        self.selection_changed.emit()


class SmartSearchBar(QWidget):
    """
    智能搜索栏，支持全局搜索、单列筛选、历史记录
    """
    
    search_changed = pyqtSignal(str)  # 搜索文本改变信号
    filter_toggled = pyqtSignal(bool)  # 筛选开关切换信号
    
    def __init__(self, show_filter_toggle: bool = True, enable_auto_complete: bool = False):
        super().__init__()
        self.show_filter_toggle = show_filter_toggle
        self.auto_complete_enabled = enable_auto_complete
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("全局搜索，多个关键字用空格隔开")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)
        
        # 筛选按钮（可选）
        if self.show_filter_toggle:
            self.filter_button = QPushButton("单列筛选")
            self.filter_button.setFixedWidth(80)
            self.filter_button.setCheckable(True)
            self.filter_button.clicked.connect(self.on_filter_toggled)
            layout.addWidget(self.filter_button)
        
        self.setLayout(layout)
    
    def set_placeholder(self, text: str):
        """设置搜索框占位文本"""
        self.search_input.setPlaceholderText(text)
    
    def get_search_text(self) -> str:
        """获取搜索文本"""
        return self.search_input.text()
    
    def clear_search(self):
        """清空搜索"""
        self.search_input.clear()
    
    def enable_auto_complete(self, data_fetcher: Callable):
        """启用自动完成功能"""
        if self.auto_complete_enabled:
            completer = QCompleter()
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.search_input.setCompleter(completer)
            
            # 设置数据获取函数
            self.auto_complete_data_fetcher = data_fetcher
            self.update_completer()
    
    def update_completer(self):
        """更新自动完成数据"""
        if hasattr(self, 'auto_complete_data_fetcher'):
            try:
                data = self.auto_complete_data_fetcher()
                model = QStringListModel(data)
                self.search_input.completer().setModel(model)
            except Exception:
                pass  # 忽略数据获取错误
    
    def on_search_changed(self, text: str):
        """搜索文本改变处理"""
        self.search_changed.emit(text)
    
    def on_filter_toggled(self, checked: bool):
        """筛选开关切换处理"""
        self.filter_toggled.emit(checked)


class BaseDialog(QDialog, DragDropMixin):
    """
    基础对话框类，提供通用功能
    """
    
    def __init__(self, title: str, parent=None, enable_drag_drop: bool = False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        
        if enable_drag_drop:
            self.enable_drag_drop()
        
        # 统一样式和行为
        self.setup_common_behavior()
    
    def setup_common_behavior(self):
        """设置通用行为：窗口大小、位置等"""
        self.resize(800, 600)
        
        # 可以在这里添加更多通用设置
        # 如字体、样式表等


class InfoBar(QHBoxLayout):
    """
    标准信息栏：标题 + 计数 + 状态显示
    """
    
    def __init__(self, spacing: int = 6):
        super().__init__()
        self.setSpacing(spacing)
        
        # 创建标签
        self.title_label = QLabel()
        self.count_label = QLabel("记录数量：0")
        self.count_label.setStyleSheet("color: #666;")
        
        self.addWidget(self.title_label)
        self.addWidget(self.count_label)
        self.addStretch()
    
    def set_title(self, title: str):
        """设置标题"""
        self.title_label.setText(title)
    
    def update_count(self, count: int, item_name: str = "项目"):
        """更新计数显示"""
        self.count_label.setText(f"{item_name}数量：{count}")
    
    def add_right_widget(self, widget):
        """在右侧添加控件"""
        self.addWidget(widget)


class SliderInputWidget(QWidget):
    """
    滑块输入组合控件：滑块 + 输入框 + 当前值显示
    """
    
    value_changed = pyqtSignal(float)
    
    def __init__(self, min_value: float = 0.5, max_value: float = 2.0, 
                 initial_value: float = 1.2, precision: int = 1):
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.precision = precision
        self.multiplier = 10 ** precision
        
        self.setup_ui(initial_value)
    
    def setup_ui(self, initial_value: float):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 输入框和当前值显示
        input_layout = QHBoxLayout()
        
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText(f'输入{self.min_value}-{self.max_value}之间的数值')
        self.value_input.textChanged.connect(self.on_input_changed)
        
        self.current_label = QLabel(f'当前值: {initial_value}')
        
        input_layout.addWidget(self.value_input)
        input_layout.addWidget(self.current_label)
        
        # 滑块
        slider_layout = QHBoxLayout()
        
        min_label = QLabel(str(self.min_value))
        
        self.slider = QSpinBox()  # 使用QSpinBox替代QSlider以支持浮点数
        self.slider.setMinimum(int(self.min_value * self.multiplier))
        self.slider.setMaximum(int(self.max_value * self.multiplier))
        self.slider.setValue(int(initial_value * self.multiplier))
        self.slider.valueChanged.connect(self.on_slider_changed)
        
        max_label = QLabel(str(self.max_value))
        
        slider_layout.addWidget(min_label)
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(max_label)
        
        layout.addLayout(input_layout)
        layout.addLayout(slider_layout)
        
        self.setLayout(layout)
        
        # 设置初始值
        self.set_value(initial_value)
    
    def get_value(self) -> float:
        """获取当前值"""
        return self.slider.value() / self.multiplier
    
    def set_value(self, value: float):
        """设置值"""
        if self.min_value <= value <= self.max_value:
            self.slider.setValue(int(value * self.multiplier))
            self.value_input.setText(str(value))
            self.current_label.setText(f'当前值: {value}')
    
    def on_input_changed(self):
        """输入框改变处理"""
        try:
            value = float(self.value_input.text())
            if self.min_value <= value <= self.max_value:
                self.slider.setValue(int(value * self.multiplier))
                self.current_label.setText(f'当前值: {value}')
                self.value_changed.emit(value)
        except ValueError:
            pass
    
    def on_slider_changed(self, int_value: int):
        """滑块改变处理"""
        value = int_value / self.multiplier
        self.value_input.setText(str(value))
        self.current_label.setText(f'当前值: {value}')
        self.value_changed.emit(value)


class FormValidator:
    """
    表单验证器，统一管理输入验证规则
    """
    
    def __init__(self):
        self.rules = {}
        self.error_messages = {}
    
    def add_rule(self, widget, validator_func: Callable, error_message: str):
        """添加验证规则"""
        widget_id = id(widget)
        self.rules[widget_id] = (widget, validator_func)
        self.error_messages[widget_id] = error_message
    
    def validate_all(self) -> tuple[bool, str]:
        """验证所有规则"""
        for widget_id, (widget, validator_func) in self.rules.items():
            try:
                if not validator_func(widget):
                    return False, self.error_messages[widget_id]
            except Exception as e:
                return False, f"验证错误: {str(e)}"
        
        return True, ""
    
    def clear_rules(self):
        """清除所有规则"""
        self.rules.clear()
        self.error_messages.clear() 


class FileNotFoundDialog:
    """
    处理文件不存在时的用户选择对话框
    统一处理"删除记录"、"替换附件"、"忽略"三个选项
    """
    
    # 定义选择结果常量
    DELETE_RECORD = "delete"
    REPLACE_ATTACHMENT = "replace"  
    IGNORE = "ignore"
    
    @staticmethod
    def show_dialog(parent, file_path: str) -> str:
        """
        显示文件不存在的选择对话框
        
        Args:
            parent: 父窗口
            file_path: 不存在的文件路径
            
        Returns:
            str: 用户选择结果 (DELETE_RECORD, REPLACE_ATTACHMENT, IGNORE)
        """
        from PyQt6.QtWidgets import QMessageBox
        
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("文件不存在")
        msg_box.setText(f"文件不存在：{file_path}")
        msg_box.setInformativeText("请选择要执行的操作：")
        
        # 添加自定义按钮
        delete_btn = msg_box.addButton("删除记录", QMessageBox.ButtonRole.ActionRole)
        add_btn = msg_box.addButton("替换附件", QMessageBox.ButtonRole.ActionRole)  
        ignore_btn = msg_box.addButton("忽略", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.setDefaultButton(ignore_btn)
        msg_box.exec()
        
        # 返回用户选择结果
        if msg_box.clickedButton() == delete_btn:
            return FileNotFoundDialog.DELETE_RECORD
        elif msg_box.clickedButton() == add_btn:
            return FileNotFoundDialog.REPLACE_ATTACHMENT
        else:
            return FileNotFoundDialog.IGNORE 