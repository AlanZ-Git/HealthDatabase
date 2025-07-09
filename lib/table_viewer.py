from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QAbstractItemView, QCheckBox,
    QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Dict, Optional
from .data_storage import DataStorage
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
        self.current_page = 1  # 当前页码
        self.records_per_page = 15  # 每页记录数，默认15
        self.total_pages = 1  # 总页数
        self.default_column_widths = {}
        self.current_column_widths = {}
        self.load_column_width_settings()
        self.load_pagination_settings()
        self.init_ui()
    
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
        self.info_layout.addStretch()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.refresh_btn.setFixedWidth(80)
        self.info_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(self.info_layout)
        
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
        # 定义列标题（添加勾选框列）
        self.headers = [
            "选择", "记录ID", "就诊日期", "医院", "科室", "医生", 
            "器官系统", "症状事由", "诊断结果", "用药信息", "备注"
        ]
        
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        
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
        
        # 为勾选框列设置固定宽度
        self.table.setColumnWidth(0, 50)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        
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
            # 获取用户的就诊记录
            self.all_records = self.data_storage.get_user_visit_records(self.current_user)
            self.calculate_pagination()
            self.update_page_display()
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败：{str(e)}")
            self.clear_table()
    
    def calculate_pagination(self):
        """计算分页信息"""
        if not self.all_records:
            self.total_pages = 1
            self.current_page = 1
            self.records = []
        else:
            self.total_pages = max(1, (len(self.all_records) + self.records_per_page - 1) // self.records_per_page)
            self.current_page = min(self.current_page, self.total_pages)
            if self.current_page < 1:
                self.current_page = 1
            
            # 计算当前页的记录
            start_index = (self.current_page - 1) * self.records_per_page
            end_index = start_index + self.records_per_page
            self.records = self.all_records[start_index:end_index]
    
    def update_page_display(self):
        """更新页面显示"""
        self.populate_table()
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
            
            # 设置空值的显示
            for col in range(1, 11):  # 从第二列开始，因为第一列是勾选框
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
        QMessageBox.information(self, "提示", "数据刷新完成")
    
    def export_data(self):
        """导出数据（预留功能）"""
        QMessageBox.information(self, "提示", "导出功能正在开发中...") 
    
    def load_column_width_settings(self):
        """加载列宽设置"""
        # 加载默认设置
        self.default_column_widths = self.load_default_column_widths()
        
        # 加载用户自定义设置（如果存在）
        self.current_column_widths = self.load_user_column_widths()
        
        # 如果没有用户自定义设置，使用默认设置
        if not self.current_column_widths:
            self.current_column_widths = self.default_column_widths.copy()
    
    def load_default_column_widths(self):
        """从settings.ini加载默认列宽设置"""
        config = configparser.ConfigParser()
        settings_file = 'settings.ini'
        default_widths = {}
        
        if os.path.exists(settings_file):
            config.read(settings_file, encoding='utf-8')
            if config.has_section('ColumnWidths'):
                for i in range(11):  # 11列（包括勾选框列）
                    key = f'column_{i}'
                    if config.has_option('ColumnWidths', key):
                        try:
                            default_widths[i] = int(config.get('ColumnWidths', key))
                        except ValueError:
                            pass
        
        # 如果没有找到设置，使用硬编码的默认值
        if not default_widths:
            default_widths = {
                0: 50, 1: 60, 2: 100, 3: 120, 4: 100, 5: 80,
                6: 100, 7: 150, 8: 150, 9: 120, 10: 100
            }
        
        return default_widths
    
    def load_user_column_widths(self):
        """从history.ini加载用户自定义列宽设置"""
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        user_widths = {}
        
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            if config.has_section('ColumnWidths'):
                for i in range(11):  # 11列（包括勾选框列）
                    key = f'column_{i}'
                    if config.has_option('ColumnWidths', key):
                        try:
                            user_widths[i] = int(config.get('ColumnWidths', key))
                        except ValueError:
                            pass
        
        return user_widths
    
    def save_user_column_widths(self):
        """保存用户自定义列宽设置到history.ini"""
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        # 读取现有的history.ini内容
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
        
        # 确保ColumnWidths节存在
        if not config.has_section('ColumnWidths'):
            config.add_section('ColumnWidths')
        
        # 保存当前列宽
        for i in range(11):  # 11列（包括勾选框列）
            width = self.table.columnWidth(i)
            config.set('ColumnWidths', f'column_{i}', str(width))
        
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
            if config.has_section('ColumnWidths'):
                config.remove_section('ColumnWidths')
                with open(history_file, 'w', encoding='utf-8') as f:
                    config.write(f)
        
        # 重新加载设置
        self.load_column_width_settings()
        
        # 应用默认列宽
        self.apply_column_widths()
    
    def apply_column_widths(self):
        """应用列宽设置到表格"""
        if not self.current_column_widths:
            return
        
        header = self.table.horizontalHeader()
        
        # 设置除勾选框列外的所有列为可拖拽调整
        for i in range(11):  # 11列（包括勾选框列）
            if i == 0:  # 勾选框列固定宽度
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(i, 50)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                if i in self.current_column_widths:
                    self.table.setColumnWidth(i, self.current_column_widths[i])
    
    def on_column_width_changed(self, logical_index, old_size, new_size):
        """列宽改变时的处理函数"""
        # 保存新的列宽到history.ini
        self.save_user_column_widths()

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
        
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            if config.has_section('Pagination'):
                if config.has_option('Pagination', 'records_per_page'):
                    try:
                        self.records_per_page = int(config.get('Pagination', 'records_per_page'))
                    except ValueError:
                        self.records_per_page = 15
                else:
                    self.records_per_page = 15
            else:
                self.records_per_page = 15
        else:
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