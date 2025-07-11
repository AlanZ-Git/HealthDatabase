from PyQt6.QtWidgets import (
    QDialog, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
import os
import subprocess
import platform
from typing import Optional

from .data_storage import DataStorage
from .ui_components import BaseDialog, StandardButtonBar, CheckableListWidget


class AttachmentDialog(BaseDialog):
    """附件管理对话框"""
    
    # 定义信号，当附件有变化时发出
    attachments_changed = pyqtSignal()
    
    def __init__(self, user_name: str, visit_record_id: int, parent=None, data_storage: Optional[DataStorage] = None):
        super().__init__(f'就诊记录 #{visit_record_id} 的附件', parent, enable_drag_drop=True)
        self.user_name = user_name
        self.visit_record_id = visit_record_id
        self.data_storage = data_storage or DataStorage()  # 使用传入的依赖或创建新实例
        
        # 设置拖拽处理函数
        self.enable_drag_drop(file_handler=self.handle_dropped_files)
        
        self.init_ui()
        self.load_attachments()
        
        self.resize(600, 400)

    def handle_dropped_files(self, file_paths):
        """处理拖拽的文件"""
        if file_paths:
            # 弹窗询问是否导入附件
            reply = QMessageBox.question(
                self,
                '确认导入',
                f'是否将{len(file_paths)}个文件导入附件？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success_count = 0
                for file_path in file_paths:
                    if self.data_storage.add_attachment_to_visit(self.user_name, self.visit_record_id, file_path):
                        success_count += 1
                
                if success_count > 0:
                    self.load_attachments()  # 重新加载列表
                    self.attachments_changed.emit()  # 发出信号
                else:
                    QMessageBox.warning(self, "失败", "附件添加失败")

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 标题信息
        title_label = QLabel(f'用户：{self.user_name}  就诊记录ID：{self.visit_record_id}')
        title_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 使用新的CheckableListWidget替代原有的附件列表
        self.attachment_list = CheckableListWidget("当前就诊记录暂无附件")
        # 双击事件
        self.attachment_list.doubleClicked.connect(self.on_attachment_double_clicked)
        layout.addWidget(self.attachment_list)
        
        # 使用StandardButtonBar创建按钮布局
        button_bar = StandardButtonBar()
        
        # 左侧按钮组
        self.add_btn = QPushButton('添加附件')
        self.add_btn.clicked.connect(self.add_attachment)
        
        self.remove_btn = QPushButton('删除选中')
        self.remove_btn.clicked.connect(self.remove_selected_attachments)
        
        self.view_btn = QPushButton('查看附件')
        self.view_btn.clicked.connect(self.view_selected_attachment)
        
        button_bar.add_left_buttons([self.add_btn, self.remove_btn, self.view_btn])
        
        # 右侧按钮组
        self.close_btn = QPushButton('关闭')
        self.close_btn.clicked.connect(self.close)
        
        button_bar.add_right_buttons([self.close_btn])
        
        layout.addLayout(button_bar)
        
        self.setLayout(layout)

    def load_attachments(self):
        """加载附件列表"""
        self.attachment_list.clear()
        
        attachments = self.data_storage.get_visit_attachments(self.user_name, self.visit_record_id)
        
        if not attachments:
            self.attachment_list.update_placeholder()
            return
        
        for attachment in attachments:
            self.attachment_list.add_checkable_item(
                text=f"{attachment['file_name']}",
                data=attachment,
                checked=False
            )

    def add_attachment(self):
        """添加附件"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择附件')
        
        if file_paths:
            success_count = 0
            for file_path in file_paths:
                if self.data_storage.add_attachment_to_visit(self.user_name, self.visit_record_id, file_path):
                    success_count += 1
            
            if success_count > 0:
                self.load_attachments()  # 重新加载列表
                self.attachments_changed.emit()  # 发出信号
            else:
                QMessageBox.warning(self, "失败", "附件添加失败")

    def remove_selected_attachments(self):
        """删除选中的附件"""
        selected_attachments = self.attachment_list.get_checked_items()
        
        # 过滤掉None值（占位符项目）
        selected_attachments = [att for att in selected_attachments if att is not None]
        
        if not selected_attachments:
            QMessageBox.information(self, "提示", "请先选择要删除的附件")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, 
            '确认删除', 
            f'确定要删除选中的 {len(selected_attachments)} 个附件吗？\n此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            for attachment in selected_attachments:
                if self.data_storage.delete_attachment(self.user_name, attachment['attachment_id']):
                    success_count += 1
            
            if success_count > 0:
                self.load_attachments()  # 重新加载列表
                self.attachments_changed.emit()  # 发出信号
            else:
                QMessageBox.warning(self, "失败", "附件删除失败")

    def view_selected_attachment(self):
        """查看选中的附件"""
        selected_item = self.attachment_list.currentItem()
        if not selected_item:
            QMessageBox.information(self, "提示", "请先选择要查看的附件")
            return
        
        attachment_data = selected_item.data(Qt.ItemDataRole.UserRole)
        if not attachment_data:
            QMessageBox.information(self, "提示", "请选择有效的附件")
            return
        
        self.open_file(attachment_data)

    def on_attachment_double_clicked(self, index):
        """双击附件时的处理"""
        item = self.attachment_list.itemFromIndex(index)
        if not item:
            return
        
        attachment_data = item.data(Qt.ItemDataRole.UserRole)
        if not attachment_data:
            return
        
        self.open_file(attachment_data)
    

    
    def replace_attachment(self, attachment_data: dict):
        """替换现有附件"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择新的附件文件')
        
        if file_paths:
            # 只取第一个文件来替换
            new_file_path = file_paths[0]
            attachment_id = attachment_data['attachment_id']
            
            # 更新附件记录的路径
            if self.data_storage.update_attachment_path(self.user_name, attachment_id, new_file_path):
                self.load_attachments()  # 重新加载列表
                self.attachments_changed.emit()  # 发出信号
            else:
                QMessageBox.warning(self, "失败", "更新附件路径失败")

    def open_file(self, attachment_data: dict):
        """打开文件"""
        file_path = attachment_data['file_path']
        
        if not os.path.exists(file_path):
            from .ui_components import FileNotFoundDialog
            
            # 使用公共对话框处理文件不存在的情况
            choice = FileNotFoundDialog.show_dialog(self, file_path)
            
            # 根据用户选择执行相应操作
            if choice == FileNotFoundDialog.DELETE_RECORD:
                # 删除附件记录
                if self.data_storage.delete_attachment(self.user_name, attachment_data['attachment_id']):
                    self.load_attachments()  # 重新加载列表
                    self.attachments_changed.emit()  # 发出信号
                else:
                    QMessageBox.warning(self, "失败", "删除附件记录失败")
            elif choice == FileNotFoundDialog.REPLACE_ATTACHMENT:
                # 替换现有附件
                self.replace_attachment(attachment_data)
            # 如果是忽略，则什么都不做
            return
        
        try:
            # 根据操作系统选择打开方式
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开文件：{str(e)}") 