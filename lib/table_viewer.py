from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QAbstractItemView
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
        self.default_column_widths = {}
        self.current_column_widths = {}
        self.load_column_width_settings()
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
        # 定义列标题
        self.headers = [
            "记录ID", "就诊日期", "医院", "科室", "医生", 
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
            self.records = self.data_storage.get_user_visit_records(self.current_user)
            self.populate_table()
            self.record_count_label.setText(f"记录数量：{len(self.records)}")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载数据失败：{str(e)}")
            self.clear_table()
    
    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.records))
        
        for row, record in enumerate(self.records):
            # 按列顺序填充数据
            items_data = [
                (str(record.get('visit_record_id', '')), 0),
                (str(record.get('date', '')), 1),
                (str(record.get('hospital', '')), 2),
                (str(record.get('department', '')), 3),
                (str(record.get('doctor', '')), 4),
                (str(record.get('organ_system', '')), 5),
                (str(record.get('reason', '')), 6),
                (str(record.get('diagnosis', '')), 7),
                (str(record.get('medication', '')), 8),
                (str(record.get('remark', '')), 9)
            ]
            
            for text, col in items_data:
                item = QTableWidgetItem(text)
                # 为每个单元格设置工具提示，显示完整内容
                if text and text != 'None':
                    item.setToolTip(text)
                self.table.setItem(row, col, item)
            
            # 设置空值的显示
            for col in range(10):
                item = self.table.item(row, col)
                if item and (item.text() == 'None' or item.text() == ''):
                    item.setText('')
                    item.setForeground(Qt.GlobalColor.gray)
                    item.setToolTip('')  # 空内容不显示提示
    
    def clear_table(self):
        """清空表格"""
        self.table.setRowCount(0)
        self.records = []
        self.record_count_label.setText("记录数量：0")
    
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
                for i in range(10):  # 10列
                    key = f'column_{i}'
                    if config.has_option('ColumnWidths', key):
                        try:
                            default_widths[i] = int(config.get('ColumnWidths', key))
                        except ValueError:
                            pass
        
        # 如果没有找到设置，使用硬编码的默认值
        if not default_widths:
            default_widths = {
                0: 60, 1: 100, 2: 120, 3: 100, 4: 80,
                5: 100, 6: 150, 7: 150, 8: 120, 9: 100
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
                for i in range(10):  # 10列
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
        for i in range(10):
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
        
        # 设置所有列为可拖拽调整
        for i in range(10):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
            if i in self.current_column_widths:
                self.table.setColumnWidth(i, self.current_column_widths[i])
    
    def on_column_width_changed(self, logical_index, old_size, new_size):
        """列宽改变时的处理函数"""
        # 保存新的列宽到history.ini
        self.save_user_column_widths()