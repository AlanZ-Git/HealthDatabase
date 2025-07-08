from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import List, Dict, Optional
from .data_storage import DataStorage


class TableViewer(QWidget):
    """数据库表格查看器"""
    
    # 定义信号
    data_updated = pyqtSignal()  # 数据更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_storage = DataStorage()
        self.current_user = None
        self.records = []
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 顶部信息栏
        self.info_layout = QHBoxLayout()
        self.user_label = QLabel("当前用户：未选择")
        self.user_label.setStyleSheet("font-weight: bold; color: #333;")
        self.record_count_label = QLabel("记录数量：0")
        self.record_count_label.setStyleSheet("color: #666;")
        
        self.info_layout.addWidget(self.user_label)
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
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ID列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # 日期列固定宽度
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # 医院列自动拉伸
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 科室列自动拉伸
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 医生列自动拉伸
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # 器官系统列自动拉伸
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)  # 就诊原因列自动拉伸
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # 诊断列自动拉伸
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)  # 用药列自动拉伸
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Stretch)  # 备注列自动拉伸
        
        # 设置固定列的宽度
        self.table.setColumnWidth(0, 60)   # ID列
        self.table.setColumnWidth(1, 100)  # 日期列
    
    def set_user(self, user_name: str):
        """设置当前用户并加载数据"""
        if user_name and user_name != '请选择用户...':
            self.current_user = user_name
            self.user_label.setText(f"当前用户：{user_name}")
            self.load_data()
        else:
            self.current_user = None
            self.user_label.setText("当前用户：未选择")
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
            self.table.setItem(row, 0, QTableWidgetItem(str(record.get('visit_record_id', ''))))
            self.table.setItem(row, 1, QTableWidgetItem(str(record.get('date', ''))))
            self.table.setItem(row, 2, QTableWidgetItem(str(record.get('hospital', ''))))
            self.table.setItem(row, 3, QTableWidgetItem(str(record.get('department', ''))))
            self.table.setItem(row, 4, QTableWidgetItem(str(record.get('doctor', ''))))
            self.table.setItem(row, 5, QTableWidgetItem(str(record.get('organ_system', ''))))
            self.table.setItem(row, 6, QTableWidgetItem(str(record.get('reason', ''))))
            self.table.setItem(row, 7, QTableWidgetItem(str(record.get('diagnosis', ''))))
            self.table.setItem(row, 8, QTableWidgetItem(str(record.get('medication', ''))))
            self.table.setItem(row, 9, QTableWidgetItem(str(record.get('remark', ''))))
            
            # 设置空值的显示
            for col in range(10):
                item = self.table.item(row, col)
                if item and (item.text() == 'None' or item.text() == ''):
                    item.setText('')
                    item.setForeground(Qt.GlobalColor.gray)
    
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