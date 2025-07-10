from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QAbstractItemView, QCheckBox,
    QSpinBox, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Dict, Optional
from .data_storage import DataStorage
from .attachment_dialog import AttachmentDialog
import configparser
import os


class TableViewer(QWidget):
    """数据库表格查看器"""
    
    # 定义信号
    data_updated = pyqtSignal()  # 数据更新信号
    visit_input_requested = pyqtSignal()  # 录入就诊信息请求信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_storage = DataStorage()
        self.current_user = None
        self.records = []
        self.all_records = []  # 存储所有记录，用于分页
        self.filtered_records = []  # 存储搜索过滤后的记录
        self.current_page = 1  # 当前页码
        self.records_per_page = 15  # 每页记录数，默认15
        self.total_pages = 1  # 总页数
        self.search_text = ""  # 当前搜索文本
        
        # 列宽度管理
        self.fixed_pixel_columns = [0, 1, 2, 5, 6, 11]  # 固定像素列：勾选框、记录ID、就诊日期、医生、器官系统、附件
        self.proportional_columns = [3, 4, 7, 8, 9, 10]  # 比例分配列：医院、科室、症状事由、诊断结果、用药信息、备注
        self.fixed_column_widths = {}  # 固定列的像素宽度
        self.proportional_column_widths = {}  # 比例列的比例值（0-1之间）
        self.is_adjusting_columns = False  # 标记是否正在调整列宽，避免递归
        
        # 单列筛选相关变量
        self.column_filter_enabled = False  # 单列筛选是否启用
        self.column_filters = {}  # 每列的筛选文本，格式：{列索引: "筛选文本"}
        self.filter_widgets = []  # 存储筛选输入框控件
        
        # 排序状态管理
        self.current_sort_column = 'visit_record_id'  # 默认按记录ID排序
        self.current_sort_order = 'ASC'  # 默认升序 (ASC/DESC)
        self.sortable_columns = {1: 'visit_record_id', 2: 'date'}  # 可排序的列：列索引->数据库字段名
        
        self.load_column_width_settings()
        self.load_pagination_settings()
        self.init_ui()

    def multi_keyword_search(self, text: str, keywords: str) -> bool:
        """
        多关键字搜索函数
        
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

    def filter_records_by_search(self, records: List[Dict], search_text: str) -> List[Dict]:
        """
        根据搜索文本过滤记录
        
        Args:
            records: 原始记录列表
            search_text: 搜索文本
            
        Returns:
            过滤后的记录列表
        """
        if not search_text.strip():
            return records  # 空搜索返回所有记录
        
        filtered = []
        
        for record in records:
            # 将记录中的所有文本字段连接起来进行搜索
            searchable_text = " ".join([
                str(record.get('visit_record_id', '')),
                str(record.get('date', '')),
                str(record.get('hospital', '')),
                str(record.get('department', '')),
                str(record.get('doctor', '')),
                str(record.get('organ_system', '')),
                str(record.get('reason', '')),
                str(record.get('diagnosis', '')),
                str(record.get('medication', '')),
                str(record.get('remark', ''))
            ])
            
            # 使用多关键字搜索函数
            if self.multi_keyword_search(searchable_text, search_text):
                filtered.append(record)
        
        return filtered
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 顶部信息栏
        self.info_layout = QHBoxLayout()
        
        # 录入就诊信息按钮（移动到这里，放在最左边）
        self.visit_input_btn = QPushButton('录入就诊信息')
        self.visit_input_btn.clicked.connect(self.on_visit_input_clicked)
        self.visit_input_btn.setFixedWidth(100)
        self.info_layout.addWidget(self.visit_input_btn)
        
        # 修改就诊信息按钮（位置在录入按钮和记录数量之间）
        self.edit_visit_btn = QPushButton('修改就诊信息')
        self.edit_visit_btn.clicked.connect(self.on_edit_visit_clicked)
        self.edit_visit_btn.setFixedWidth(100)
        self.edit_visit_btn.setEnabled(False)  # 初始状态禁用
        self.info_layout.addWidget(self.edit_visit_btn)
        
        # 移除原来的用户标签，因为主界面已经显示了
        self.record_count_label = QLabel("记录数量：0")
        self.record_count_label.setStyleSheet("color: #666;")
        
        self.info_layout.addWidget(self.record_count_label)
        
        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("全局搜索，多个关键字用空格隔开")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.info_layout.addWidget(self.search_input)
        
        # 单列筛选按钮
        self.column_filter_btn = QPushButton("单列筛选")
        self.column_filter_btn.clicked.connect(self.toggle_column_filter)
        self.column_filter_btn.setFixedWidth(80)
        self.column_filter_btn.setCheckable(True)
        self.info_layout.addWidget(self.column_filter_btn)
        
        self.info_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setFixedWidth(80)
        self.info_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(self.info_layout)
        
        # 单列筛选输入框行（初始隐藏，放在表格上方）
        self.filter_layout = QHBoxLayout()
        self.filter_layout.setSpacing(0)  # 确保输入框之间没有间距，与表格列对齐
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建筛选输入框
        self.create_filter_widgets()
        
        # 添加筛选行到布局（初始隐藏）
        self.filter_widget = QWidget()
        self.filter_widget.setLayout(self.filter_layout)
        self.filter_widget.setVisible(False)
        layout.addWidget(self.filter_widget)
        
        # 表格
        self.table = QTableWidget()
        self.init_table()
        layout.addWidget(self.table)
        
        # 底部操作栏
        self.button_layout = QHBoxLayout()
        
        # 分页控件（从左边开始）
        # 每页记录数设置
        self.page_size_label = QLabel("每页")
        self.button_layout.addWidget(self.page_size_label)
        
        self.page_size_spinbox = QSpinBox()
        self.page_size_spinbox.setMinimum(1)
        self.page_size_spinbox.setMaximum(1000)
        self.page_size_spinbox.setValue(self.records_per_page)
        self.page_size_spinbox.valueChanged.connect(self.on_page_size_changed)
        self.page_size_spinbox.setFixedWidth(60)
        self.button_layout.addWidget(self.page_size_spinbox)
        
        self.page_size_label2 = QLabel("条记录")
        self.button_layout.addWidget(self.page_size_label2)
        
        # 添加间距
        self.button_layout.addSpacing(20)
        
        # 分页按钮
        self.first_page_btn = QPushButton("首页")
        self.first_page_btn.clicked.connect(self.go_to_first_page)
        self.first_page_btn.setFixedWidth(60)
        self.button_layout.addWidget(self.first_page_btn)
        
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.go_to_prev_page)
        self.prev_page_btn.setFixedWidth(70)
        self.button_layout.addWidget(self.prev_page_btn)
        
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.go_to_next_page)
        self.next_page_btn.setFixedWidth(70)
        self.button_layout.addWidget(self.next_page_btn)
        
        self.last_page_btn = QPushButton("末页")
        self.last_page_btn.clicked.connect(self.go_to_last_page)
        self.last_page_btn.setFixedWidth(60)
        self.button_layout.addWidget(self.last_page_btn)
        
        # 页码信息
        self.page_info_label = QLabel("第1页 / 共1页")
        self.button_layout.addWidget(self.page_info_label)
        
        self.button_layout.addStretch()
        
        # 导出按钮（预留）
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        self.export_btn.setEnabled(False)  # 暂时禁用
        self.button_layout.addWidget(self.export_btn)
        
        layout.addLayout(self.button_layout)
        
        self.setLayout(layout)
    
    def init_table(self):
        """初始化表格"""
        # 定义列标题（添加勾选框列和附件列）
        self.headers = [
            "选择", "记录ID", "就诊日期", "医院", "科室", "医生", 
            "器官系统", "症状事由", "诊断结果", "用药信息", "备注", "附件"
        ]
        
        self.table.setColumnCount(len(self.headers))
        # 先设置基础标题，然后更新为包含排序指示器的标题
        self.table.setHorizontalHeaderLabels(self.headers)
        self.update_header_labels()
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)  # 交替行颜色
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)  # 选择整行
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)  # 不可编辑
        self.table.verticalHeader().setVisible(False)  # 隐藏左侧行号
        
        # 设置工具提示样式
        # 获取当前字体大小并乘以1.3倍
        current_font = self.table.font()
        tooltip_font_size = int(current_font.pointSize() * 1.3)
        
        # 设置工具提示样式：背景色RGB(244, 236, 145)，字体大小增加
        tooltip_style = f"""
        QToolTip {{
            background-color: rgb(244, 236, 145);
            color: black;
            border: 1px solid #999;
            padding: 5px;
            font-size: {tooltip_font_size}pt;
            border-radius: 3px;
        }}
        """
        self.table.setStyleSheet(tooltip_style)
        
        # 设置平滑滚动 - 优化横向拖动条移动
        h_scrollbar = self.table.horizontalScrollBar()
        h_scrollbar.setSingleStep(1)  # 设置单步滚动像素数，越小越平滑
        h_scrollbar.setPageStep(10)   # 设置页滚动像素数
        
        v_scrollbar = self.table.verticalScrollBar()
        v_scrollbar.setSingleStep(1)  # 设置垂直滚动单步为1行
        v_scrollbar.setPageStep(10)   # 设置垂直滚动页步为10行
        
        # 应用列宽设置
        self.apply_column_widths()
        
        # 连接列宽变化信号
        header = self.table.horizontalHeader()
        header.sectionResized.connect(self.on_column_width_changed)
        
        # 连接标题点击信号，支持排序
        header.sectionClicked.connect(self.on_header_clicked)
        
        # 连接双击信号
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        
        # 连接单击信号
        self.table.clicked.connect(self.on_table_clicked)
    
    def on_visit_input_clicked(self):
        """录入就诊信息按钮点击事件"""
        self.visit_input_requested.emit()  # 发出信号给主界面处理
    
    def set_user(self, user_name: str):
        """设置当前用户并加载数据"""
        if user_name and user_name != '请选择用户...':
            self.current_user = user_name
            self.load_data()
        else:
            self.current_user = None
            self.clear_table()
    
    def load_data(self):
        """加载数据"""
        if not self.current_user:
            self.clear_table()
            return
        
        try:
            # 获取用户的就诊记录，传递当前排序参数
            self.all_records = self.data_storage.get_user_visit_records(
                self.current_user, 
                self.current_sort_column, 
                self.current_sort_order
            )
            
            # 先应用全局搜索过滤
            self.filtered_records = self.filter_records_by_search(self.all_records, self.search_text)
            
            # 再应用单列筛选过滤
            self.filtered_records = self.filter_records_by_column(self.filtered_records)
            
            self.calculate_pagination()
            self.update_page_display()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败：{str(e)}")
            self.clear_table()
    
    def calculate_pagination(self):
        """计算分页信息"""
        if not self.filtered_records:
            self.total_pages = 1
            self.current_page = 1
            self.records = []
        else:
            self.total_pages = max(1, (len(self.filtered_records) + self.records_per_page - 1) // self.records_per_page)
            self.current_page = min(self.current_page, self.total_pages)
            if self.current_page < 1:
                self.current_page = 1
            
            # 计算当前页的记录
            start_index = (self.current_page - 1) * self.records_per_page
            end_index = start_index + self.records_per_page
            self.records = self.filtered_records[start_index:end_index]
    
    def update_page_display(self):
        """更新页面显示"""
        self.populate_table()
        
        # 显示过滤后的记录数量，如果有搜索条件，同时显示总数
        if self.search_text.strip():
            self.record_count_label.setText(f"记录数量：{len(self.filtered_records)} (共{len(self.all_records)}条)")
        else:
            self.record_count_label.setText(f"记录数量：{len(self.all_records)}")
        
        # 更新页码信息
        if self.total_pages > 0:
            self.page_info_label.setText(f"第{self.current_page}页 / 共{self.total_pages}页")
        else:
            self.page_info_label.setText("第1页 / 共1页")
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)
    
    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.records))
        
        for row, record in enumerate(self.records):
            # 第一列：勾选框
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin: 5px; }")
            checkbox.stateChanged.connect(self.on_checkbox_state_changed)
            self.table.setCellWidget(row, 0, checkbox)
            
            # 按列顺序填充数据（列索引需要偏移1）
            items_data = [
                (str(record.get('visit_record_id', '')), 1),
                (str(record.get('date', '')), 2),
                (str(record.get('hospital', '')), 3),
                (str(record.get('department', '')), 4),
                (str(record.get('doctor', '')), 5),
                (str(record.get('organ_system', '')), 6),
                (str(record.get('reason', '')), 7),
                (str(record.get('diagnosis', '')), 8),
                (str(record.get('medication', '')), 9),
                (str(record.get('remark', '')), 10)
            ]
            
            for text, col in items_data:
                item = QTableWidgetItem(text)
                # 为每个单元格设置工具提示，显示完整内容
                if text and text != 'None':
                    item.setToolTip(text)
                self.table.setItem(row, col, item)
            
            # 最后一列：附件按钮
            visit_record_id = record.get('visit_record_id')
            
            # 检查是否有附件，设置按钮文字
            has_attachments = False
            if visit_record_id is not None and self.current_user:
                attachments = self.data_storage.get_visit_attachments(self.current_user, int(visit_record_id))
                has_attachments = len(attachments) > 0
            
            # 根据是否有附件设置按钮文字
            btn_text = "附件" if has_attachments else "无附件"
            attachment_btn = QPushButton(btn_text)
            attachment_btn.setStyleSheet("QPushButton { margin: 2px; }")
            
            # 将visit_record_id存储在按钮中，用于点击时识别，点击逻辑不变
            if visit_record_id is not None:
                attachment_btn.clicked.connect(lambda checked, vid=int(visit_record_id): self.on_attachment_btn_clicked(vid))
            self.table.setCellWidget(row, 11, attachment_btn)
            
            # 设置空值的显示
            for col in range(1, 11):  # 从第二列开始到第十一列，因为第一列是勾选框，最后一列是附件按钮
                item = self.table.item(row, col)
                if item and (item.text() == 'None' or item.text() == ''):
                    item.setText('')
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setToolTip('')  # 空内容不显示提示
    
    def clear_table(self):
        """清空表格"""
        self.table.setRowCount(0)
        self.records = []
        self.all_records = []
        self.filtered_records = [] # 清空过滤后的记录
        self.current_page = 1
        self.total_pages = 1
        self.record_count_label.setText("记录数量：0")
        self.page_info_label.setText("第1页 / 共1页")
        
        # 更新按钮状态
        self.first_page_btn.setEnabled(False)
        self.prev_page_btn.setEnabled(False)
        self.next_page_btn.setEnabled(False)
        self.last_page_btn.setEnabled(False)
    
    def refresh_data(self):
        """刷新数据"""
        self.load_data()
    
    def export_data(self):
        """导出数据（预留功能）"""
        QMessageBox.information(self, "提示", "导出功能正在开发中...") 
    
    def load_column_width_settings(self):
        """加载列宽设置"""
        # 加载默认设置
        self.load_default_column_widths()
        
        # 加载用户自定义设置（如果存在）
        self.load_user_column_widths()
    
    def load_default_column_widths(self):
        """从settings.ini加载默认列宽设置"""
        config = configparser.ConfigParser()
        settings_file = 'settings.ini'
        
        # 设置默认值
        default_fixed_widths = {
            0: 50, 1: 60, 2: 100, 5: 80, 6: 100, 11: 80
        }
        default_proportional_widths = {
            3: 0.2, 4: 0.15, 7: 0.25, 8: 0.25, 9: 0.15, 10: 0.15  # 比例总和为1.15，会自动归一化
        }
        
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            
            # 读取固定像素列设置
            if config.has_section('FixedColumnWidths'):
                for col in self.fixed_pixel_columns:
                    key = f'column_{col}'
                    if config.has_option('FixedColumnWidths', key):
                        try:
                            default_fixed_widths[col] = int(config.get('FixedColumnWidths', key))
                        except ValueError:
                            pass
            
            # 读取比例列设置
            if config.has_section('ProportionalColumnWidths'):
                for col in self.proportional_columns:
                    key = f'column_{col}'
                    if config.has_option('ProportionalColumnWidths', key):
                        try:
                            default_proportional_widths[col] = float(config.get('ProportionalColumnWidths', key))
                        except ValueError:
                            pass
        
        # 设置默认宽度
        self.fixed_column_widths = default_fixed_widths.copy()
        
        # 归一化比例值，确保总和为1
        total_proportion = sum(default_proportional_widths.values())
        if total_proportion > 0:
            self.proportional_column_widths = {
                col: proportion / total_proportion 
                for col, proportion in default_proportional_widths.items()
            }
        else:
            # 如果没有比例设置，平均分配
            self.proportional_column_widths = {
                col: 1.0 / len(self.proportional_columns) 
                for col in self.proportional_columns
            }
    
    def load_user_column_widths(self):
        """从history.ini加载用户自定义列宽设置"""
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            
            # 读取固定像素列的用户设置
            if config.has_section('FixedColumnWidths'):
                for col in self.fixed_pixel_columns:
                    key = f'column_{col}'
                    if config.has_option('FixedColumnWidths', key):
                        try:
                            self.fixed_column_widths[col] = int(config.get('FixedColumnWidths', key))
                        except ValueError:
                            pass
            
            # 读取比例列的用户设置
            if config.has_section('ProportionalColumnWidths'):
                user_proportions = {}
                for col in self.proportional_columns:
                    key = f'column_{col}'
                    if config.has_option('ProportionalColumnWidths', key):
                        try:
                            user_proportions[col] = float(config.get('ProportionalColumnWidths', key))
                        except ValueError:
                            pass
                
                # 如果有用户设置的比例，归一化后使用
                if user_proportions:
                    total_proportion = sum(user_proportions.values())
                    if total_proportion > 0:
                        self.proportional_column_widths.update({
                            col: proportion / total_proportion 
                            for col, proportion in user_proportions.items()
                        })
    
    def save_user_column_widths(self):
        """保存用户自定义列宽设置到history.ini"""
        if self.is_adjusting_columns:
            return  # 如果正在批量调整列宽，不保存
            
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        # 读取现有的history.ini内容
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
        
        # 确保节存在
        if not config.has_section('FixedColumnWidths'):
            config.add_section('FixedColumnWidths')
        if not config.has_section('ProportionalColumnWidths'):
            config.add_section('ProportionalColumnWidths')
        
        # 保存固定列宽度
        for col in self.fixed_pixel_columns:
            width = self.table.columnWidth(col)
            config.set('FixedColumnWidths', f'column_{col}', str(width))
            self.fixed_column_widths[col] = width
        
        # 计算并保存比例列的比例
        total_proportional_width = sum(
            self.table.columnWidth(col) for col in self.proportional_columns
        )
        
        if total_proportional_width > 0:
            for col in self.proportional_columns:
                proportion = self.table.columnWidth(col) / total_proportional_width
                config.set('ProportionalColumnWidths', f'column_{col}', str(proportion))
                self.proportional_column_widths[col] = proportion
        
        # 写入文件
        with open(history_file, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def reset_to_default_column_widths(self):
        """重置列宽为默认设置"""
        # 删除history.ini中的列宽设置
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            if config.has_section('FixedColumnWidths'):
                config.remove_section('FixedColumnWidths')
            if config.has_section('ProportionalColumnWidths'):
                config.remove_section('ProportionalColumnWidths')
            # 保留其他部分，只删除列宽设置
            with open(history_file, 'w', encoding='utf-8') as f:
                config.write(f)
        
        # 重新加载设置
        self.load_column_width_settings()
        
        # 应用默认列宽
        self.apply_column_widths()
    
    def calculate_proportional_widths(self):
        """计算比例列的实际像素宽度"""
        # 获取表格总宽度
        table_width = self.table.width()
        
        # 减去固定列的宽度
        fixed_total_width = sum(self.fixed_column_widths.values())
        
        # 减去滚动条宽度（大约16-20像素）
        scrollbar_width = 20
        
        # 可用于比例分配的宽度
        available_width = max(200, table_width - fixed_total_width - scrollbar_width)
        
        # 计算各比例列的实际宽度
        proportional_widths = {}
        for col in self.proportional_columns:
            proportion = self.proportional_column_widths.get(col, 1.0 / len(self.proportional_columns))
            proportional_widths[col] = max(50, int(available_width * proportion))  # 最小宽度50像素
        
        return proportional_widths
    
    def apply_column_widths(self):
        """应用列宽设置到表格"""
        if not hasattr(self.table, 'horizontalHeader'):
            return
            
        self.is_adjusting_columns = True  # 标记正在调整列宽
        
        header = self.table.horizontalHeader()
        
        # 计算比例列的实际宽度
        proportional_widths = self.calculate_proportional_widths()
        
        # 设置所有列为可交互模式（允许拖拽）
        for i in range(12):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # 设置固定列宽度
        for col, width in self.fixed_column_widths.items():
            self.table.setColumnWidth(col, width)
        
        # 设置比例列宽度
        for col, width in proportional_widths.items():
            self.table.setColumnWidth(col, width)
        
        self.is_adjusting_columns = False  # 结束调整标记
        
        # 如果单列筛选已启用，更新筛选输入框的宽度
        if self.column_filter_enabled:
            self.update_filter_widget_sizes()
    
    def on_column_width_changed(self, logical_index, old_size, new_size):
        """列宽改变时的处理函数"""
        if self.is_adjusting_columns:
            return  # 如果正在批量调整，不处理
            
        # 保存新的列宽到history.ini
        self.save_user_column_widths()
        
        # 如果单列筛选已启用，更新对应筛选输入框的宽度
        if self.column_filter_enabled and logical_index < len(self.filter_widgets):
            self.filter_widgets[logical_index].setFixedWidth(new_size)
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        # 当窗口大小改变时，重新计算比例列的宽度
        if hasattr(self, 'table') and self.table is not None:
            self.apply_column_widths()

    def on_header_clicked(self, logical_index):
        """表格标题点击事件处理，实现排序功能"""
        # 只有记录ID和就诊日期列支持排序
        if logical_index not in self.sortable_columns:
            return
        
        # 获取当前点击的列对应的数据库字段名
        clicked_column = self.sortable_columns[logical_index]
        
        # 如果点击的是当前排序列，则切换排序顺序
        if clicked_column == self.current_sort_column:
            self.current_sort_order = 'DESC' if self.current_sort_order == 'ASC' else 'ASC'
        else:
            # 如果点击的是不同的列，则设置为新的排序列，默认升序
            self.current_sort_column = clicked_column
            self.current_sort_order = 'ASC'
        
        # 更新表格标题显示（显示排序指示器）
        self.update_header_labels()
        
        # 重新加载数据以应用新的排序
        if self.current_user:
            self.load_data()

    def update_header_labels(self):
        """更新表格标题，显示排序指示器"""
        # 基础标题（不包含排序指示器）
        base_headers = [
            "选择", "记录ID", "就诊日期", "医院", "科室", "医生", 
            "器官系统", "症状事由", "诊断结果", "用药信息", "备注", "附件"
        ]
        
        # 复制基础标题
        updated_headers = base_headers.copy()
        
        # 为当前排序列添加排序指示器
        for col_index, db_field in self.sortable_columns.items():
            if db_field == self.current_sort_column:
                # 根据排序顺序选择三角形符号
                if self.current_sort_order == 'ASC':
                    indicator = " ▲"  # 升序：尖朝上的黑色三角形
                else:
                    indicator = " ▼"  # 降序：尖朝下的黑色三角形
                
                # 在对应列标题后添加指示器
                updated_headers[col_index] = base_headers[col_index] + indicator
        
        # 更新表格标题
        self.table.setHorizontalHeaderLabels(updated_headers)

    def on_checkbox_state_changed(self):
        """勾选框状态改变时的处理函数"""
        checked_count = self.get_checked_rows_count()
        
        # 如果选中了一行，启用修改按钮；如果选中超过一行或没有选中，禁用修改按钮
        if checked_count == 1:
            self.edit_visit_btn.setEnabled(True)
        else:
            self.edit_visit_btn.setEnabled(False)

    def get_checked_rows_count(self):
        """获取勾选的行数"""
        count = 0
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                count += 1
        return count

    def get_checked_record(self):
        """获取当前勾选的记录数据（仅在勾选一行时返回）"""
        checked_rows = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                checked_rows.append(row)
        
        if len(checked_rows) != 1:
            return None
        
        # 在分页情况下，需要使用当前页显示的记录
        row = checked_rows[0]
        if 0 <= row < len(self.records):
            return self.records[row]
        
        return None

    def on_table_clicked(self, index):
        """单击表格行时切换勾选状态"""
        if not self.current_user:
            return
        
        # 获取单击的行
        row = index.row()
        if 0 <= row < self.table.rowCount():
            # 获取该行的勾选框
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                # 切换勾选状态
                checkbox.setChecked(not checkbox.isChecked())

    def on_table_double_clicked(self, index):
        """双击表格行时进入修改模式"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        # 获取双击的行（在分页情况下使用当前页的记录）
        row = index.row()
        if 0 <= row < len(self.records):
            record = self.records[row]
            
            # 导入对话框类
            from .visit_record_dialog import VisitRecordDialog
            
            # 打开编辑模式的对话框
            dialog = VisitRecordDialog(
                user_name=self.current_user,
                parent=self,
                edit_record=record
            )
            
            # 连接信号，当记录更新后刷新表格
            dialog.record_uploaded.connect(self.load_data)
            
            # 显示对话框
            dialog.exec()

    def on_edit_visit_clicked(self):
        """修改就诊信息按钮点击事件"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        # 获取勾选的记录
        selected_record = self.get_checked_record()
        if not selected_record:
            QMessageBox.warning(self, "错误", "请勾选要修改的记录")
            return
        
        # 导入对话框类
        from .visit_record_dialog import VisitRecordDialog
        
        # 打开编辑模式的对话框
        dialog = VisitRecordDialog(
            user_name=self.current_user,
            parent=self,
            edit_record=selected_record
        )
        
        # 连接信号，当记录更新后刷新表格
        dialog.record_uploaded.connect(self.load_data)
        
        # 显示对话框
        dialog.exec()
    
    def on_page_size_changed(self, value):
        """每页记录数改变事件"""
        self.records_per_page = value
        self.current_page = 1  # 重置到第一页
        self.save_pagination_settings()
        
        if self.current_user:
            self.calculate_pagination()
            self.update_page_display()
    
    def go_to_first_page(self):
        """跳转到首页"""
        if self.current_page != 1:
            self.current_page = 1
            self.calculate_pagination()
            self.update_page_display()
    
    def go_to_prev_page(self):
        """跳转到上一页"""
        if self.current_page > 1:
            self.current_page -= 1
            self.calculate_pagination()
            self.update_page_display()
    
    def go_to_next_page(self):
        """跳转到下一页"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.calculate_pagination()
            self.update_page_display()
    
    def go_to_last_page(self):
        """跳转到末页"""
        if self.current_page != self.total_pages:
            self.current_page = self.total_pages
            self.calculate_pagination()
            self.update_page_display()
    
    def load_pagination_settings(self):
        """加载分页设置"""
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        # 首先尝试从 history.ini 加载用户设置
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            if config.has_section('Pagination'):
                if config.has_option('Pagination', 'records_per_page'):
                    try:
                        self.records_per_page = int(config.get('Pagination', 'records_per_page'))
                        return  # 成功加载用户设置，直接返回
                    except ValueError:
                        pass
        
        # 如果 history.ini 没有设置，则从 settings.ini 加载默认设置
        settings_file = 'settings.ini'
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            if config.has_section('Pagination'):
                if config.has_option('Pagination', 'records_per_page'):
                    try:
                        self.records_per_page = int(config.get('Pagination', 'records_per_page'))
                        return  # 成功加载默认设置，直接返回
                    except ValueError:
                        pass
        
        # 如果都没有找到设置，使用硬编码默认值
        self.records_per_page = 15
    
    def save_pagination_settings(self):
        """保存分页设置"""
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        # 读取现有的history.ini内容
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
        
        # 确保Pagination节存在
        if not config.has_section('Pagination'):
            config.add_section('Pagination')
        
        # 保存每页记录数设置
        config.set('Pagination', 'records_per_page', str(self.records_per_page))
        
        # 写入文件
        with open(history_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def on_attachment_btn_clicked(self, visit_record_id: int):
        """附件按钮点击事件处理"""
        if not self.current_user:
            QMessageBox.warning(self, "错误", "请先选择用户")
            return
        
        # 打开附件管理对话框
        dialog = AttachmentDialog(self.current_user, visit_record_id, self)
        dialog.attachments_changed.connect(self.refresh_data)  # 连接信号，当附件变化时刷新数据
        dialog.exec()

    def on_search_text_changed(self, text):
        """搜索文本改变时的处理函数"""
        self.search_text = text
        self.current_page = 1  # 重置到第一页
        self.load_data()  # 重新加载数据以应用新的搜索过滤
    
    def create_filter_widgets(self):
        """创建单列筛选输入框"""
        # 清除现有的筛选控件
        for widget in self.filter_widgets:
            widget.deleteLater()
        self.filter_widgets.clear()
        
        # 定义列标题（与init_table中的headers保持一致）
        headers = [
            "选择", "记录ID", "就诊日期", "医院", "科室", "医生", 
            "器官系统", "症状事由", "诊断结果", "用药信息", "备注", "附件"
        ]
        
        # 为每一列创建筛选输入框
        for i in range(len(headers)):
            filter_input = QLineEdit()
            filter_input.setPlaceholderText(f"筛选{headers[i]}")
            filter_input.textChanged.connect(lambda text, col=i: self.on_column_filter_changed(col, text))
            
            # 为勾选框列和附件列禁用筛选
            if i == 0 or i == 11:  # 选择列和附件列
                filter_input.setEnabled(False)
                filter_input.setPlaceholderText("")
            
            self.filter_widgets.append(filter_input)
            self.filter_layout.addWidget(filter_input)
        
        # 初始更新筛选控件大小
        self.update_filter_widget_sizes()
    
    def toggle_column_filter(self):
        """切换单列筛选的开启/关闭状态"""
        self.column_filter_enabled = not self.column_filter_enabled
        self.filter_widget.setVisible(self.column_filter_enabled)
        
        # 更新按钮状态
        self.column_filter_btn.setChecked(self.column_filter_enabled)
        
        if self.column_filter_enabled:
            # 开启时更新筛选控件大小
            self.update_filter_widget_sizes()
        else:
            # 关闭时清除所有筛选条件
            self.column_filters.clear()
            for filter_input in self.filter_widgets:
                filter_input.clear()
            self.load_data()  # 重新加载数据
    
    def update_filter_widget_sizes(self):
        """更新筛选输入框的宽度以匹配表格列宽"""
        if not self.column_filter_enabled or not self.filter_widgets:
            return
        
        # 清除所有间距，确保输入框紧密排列如同表格列
        self.filter_layout.setSpacing(0)
        
        # 获取表格的左边框宽度
        frame_width = self.table.frameWidth()
        
        # 计算准确的左边距：表格左边框 + 可能的行头部宽度（已隐藏，所以为0）
        left_margin = frame_width
        
        # 设置筛选布局边距，与表格精确对齐
        self.filter_layout.setContentsMargins(left_margin, 0, frame_width, 0)
        
        for i, filter_input in enumerate(self.filter_widgets):
            column_width = self.table.columnWidth(i)
            filter_input.setFixedWidth(column_width)
            filter_input.setMinimumWidth(column_width)
            filter_input.setMaximumWidth(column_width)
            
            # 设置输入框样式，确保无额外边距
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
    
    def on_column_filter_changed(self, column_index: int, text: str):
        """单列筛选文本改变时的处理函数"""
        if text.strip():
            self.column_filters[column_index] = text.strip()
        else:
            # 如果筛选文本为空，移除该列的筛选条件
            if column_index in self.column_filters:
                del self.column_filters[column_index]
        
        self.current_page = 1  # 重置到第一页
        self.load_data()  # 重新加载数据以应用新的筛选
    
    def filter_records_by_column(self, records: List[Dict]) -> List[Dict]:
        """
        根据单列筛选条件过滤记录
        
        Args:
            records: 原始记录列表
            
        Returns:
            过滤后的记录列表
        """
        if not self.column_filters:
            return records  # 没有筛选条件，返回所有记录
        
        filtered = []
        
        # 定义列索引与记录字段的映射关系
        column_field_mapping = {
            1: 'visit_record_id',
            2: 'date',
            3: 'hospital',
            4: 'department',
            5: 'doctor',
            6: 'organ_system',
            7: 'reason',
            8: 'diagnosis',
            9: 'medication',
            10: 'remark'
        }
        
        for record in records:
            # 检查每个筛选条件
            match_all_filters = True
            
            for column_index, filter_text in self.column_filters.items():
                # 获取该列对应的字段名
                field_name = column_field_mapping.get(column_index)
                if not field_name:
                    continue  # 跳过不支持筛选的列
                
                # 获取该字段的值
                field_value = str(record.get(field_name, ''))
                
                # 使用多关键字搜索函数检查是否匹配
                if not self.multi_keyword_search(field_value, filter_text):
                    match_all_filters = False
                    break
            
            # 只有匹配所有筛选条件的记录才会被保留
            if match_all_filters:
                filtered.append(record)
        
        return filtered