import sys
import os
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QInputDialog
)
from PyQt6.QtCore import QEvent
from PyQt6.QtGui import QIcon
from lib.data_storage import DataStorage
from lib.table_viewer import TableViewer
from lib.visit_record_dialog import VisitRecordDialog
from lib.settings_manager import SettingsManager
from lib.config_manager import ConfigManager
from lib.ui_components import StandardButtonBar


class VisitInputWidget(QWidget):
    def __init__(self, data_storage: Optional[DataStorage] = None, config_manager: Optional[ConfigManager] = None, app: Optional[QApplication] = None):
        super().__init__()
        self.setWindowTitle('就诊记录')
        self.data_storage = data_storage or DataStorage()  # 使用传入的依赖或创建新实例
        self.config_manager = config_manager or ConfigManager()  # 使用传入的依赖或创建新实例
        self.app = app  # 主应用程序引用，用于字体设置
        
        # 跟踪窗口状态，用于检测最大化状态变化
        self._was_maximized = False
        
        # 加载窗口设置
        self.config_manager.apply_window_settings(self)
        # 更新初始最大化状态
        self._was_maximized = self.isMaximized()
        
        self.init_ui()

    def init_ui(self):
        # 使用StandardButtonBar创建用户管理布局
        user_layout = StandardButtonBar()
        
        # 左侧区域：用户选择和操作按钮
        user_label = QLabel('选择用户')
        user_layout.addWidget(user_label)
        
        self.user_combo = QComboBox()
        self.user_combo.addItem('请选择用户...')
        self.user_combo.setMinimumWidth(208)
        # 当用户选择改变时，更新医院名称自动完成列表
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        user_layout.addWidget(self.user_combo)
        
        # 用户操作按钮组
        self.create_user_btn = QPushButton('创建新用户')
        self.create_user_btn.clicked.connect(self.create_new_user)
        
        self.delete_user_btn = QPushButton('删除用户')
        self.delete_user_btn.clicked.connect(self.delete_user)
        
        user_layout.add_left_buttons([self.create_user_btn, self.delete_user_btn])
        
        # 右侧区域：设置按钮
        self.settings_btn = QPushButton('设置')
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setFixedWidth(80)  # 设置固定宽度，与刷新按钮保持一致
        
        user_layout.add_right_buttons([self.settings_btn])
        
        # 读取data文件夹下的sqlite文件
        self.load_users()

        # 表格查看区域（直接嵌入，不使用Tab），传递依赖
        self.table_viewer = TableViewer(data_storage=self.data_storage, config_manager=self.config_manager)
        # 连接信号，处理录入就诊信息的请求
        self.table_viewer.visit_input_requested.connect(self.open_visit_input_dialog)
        
        # 加载上次选择的用户（必须在table_viewer创建之后）
        self.load_last_user()
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(user_layout)
        main_layout.addWidget(self.table_viewer)
        main_layout.setSpacing(10)
        
        self.setLayout(main_layout)

    def load_users(self):
        """加载用户列表"""
        users = self.data_storage.get_all_users()
        # 清空现有选项（保留'请选择用户...'）
        while self.user_combo.count() > 1:
            self.user_combo.removeItem(1)
        # 添加用户
        for user in users:
            self.user_combo.addItem(user)

    def load_last_user(self):
        """加载上次选择的用户"""
        last_user = self.config_manager.get_last_user()
        if last_user:
            # 在下拉框中查找并选择该用户
            index = self.user_combo.findText(last_user)
            if index >= 0:
                self.user_combo.setCurrentIndex(index)
                # 修复：手动触发用户数据加载
                self.on_user_changed()

    def closeEvent(self, event):
        """窗口关闭事件：保存窗口设置"""
        self.config_manager.save_window_settings(self)
        event.accept()
    
    def changeEvent(self, event):
        """窗口状态变化事件：处理最大化状态变化"""
        super().changeEvent(event)
        
        if event.type() == QEvent.Type.WindowStateChange:
            current_maximized = self.isMaximized()
            
            # 检测从最大化变为正常状态
            if self._was_maximized and not current_maximized:
                # 从最大化退出到正常模式，应用保存的窗口大小和位置
                self._apply_saved_window_geometry()
            
            # 更新最大化状态跟踪
            self._was_maximized = current_maximized
    
    def _apply_saved_window_geometry(self):
        """应用保存的窗口大小和位置（用于从最大化退出时）"""
        # 获取保存的窗口大小和位置
        width, height = self.config_manager.get_window_size()
        position = self.config_manager.get_window_position()
        
        # 应用窗口大小
        self.resize(width, height)
        
        # 应用窗口位置
        if position:
            self.move(position[0], position[1])
        else:
            self.config_manager.center_window_on_screen(self)

    def create_new_user(self):
        """创建新用户"""
        user_name, ok = QInputDialog.getText(self, '创建新用户', '请输入用户名:')
        if ok and user_name.strip():
            user_name = user_name.strip()
            # 检查用户名是否已存在
            existing_users = self.data_storage.get_all_users()
            if user_name in existing_users:
                QMessageBox.warning(self, '警告', f'用户名 "{user_name}" 已存在！')
                return
            
            # 使用data_storage创建用户
            if self.data_storage.create_user(user_name):
                self.user_combo.addItem(user_name)
                self.user_combo.setCurrentText(user_name)
                QMessageBox.information(self, '成功', f'用户 "{user_name}" 创建成功！')
            else:
                QMessageBox.warning(self, '错误', f'创建用户 "{user_name}" 失败！')

    def delete_user(self):
        """删除用户"""
        # 获取所有用户列表
        users = self.data_storage.get_all_users()
        if not users:
            QMessageBox.information(self, '提示', '没有可删除的用户！')
            return
        
        # 获取当前选中的用户，确定默认选择的索引
        current_user = self.user_combo.currentText()
        default_index = 0  # 默认选择第一个
        
        # 如果当前用户不是"请选择用户..."，则在用户列表中查找该用户的索引
        if current_user != '请选择用户...' and current_user in users:
            default_index = users.index(current_user)
        
        # 弹窗让用户选择要删除的用户
        user_name, ok = QInputDialog.getItem(
            self, 
            '选择要删除的用户', 
            '请选择要删除的用户:',
            users,
            default_index,  # 默认选择当前用户
            False  # 不允许编辑
        )
        
        if ok and user_name:
            # 确认删除时再次警告
            reply = QMessageBox.question(
                self,
                '确认删除',
                f'确定要删除用户 "{user_name}" 吗？\n\n⚠️ 警告：本操作会删除该用户的所有就诊记录！\n此操作不可恢复！',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 使用data_storage删除用户
                if self.data_storage.delete_user(user_name):
                    # 从下拉框中移除
                    index = self.user_combo.findText(user_name)
                    if index >= 0:
                        self.user_combo.removeItem(index)
                    QMessageBox.information(self, '成功', f'用户 "{user_name}" 及其所有就诊记录已删除！')
                else:
                    QMessageBox.warning(self, '错误', f'删除用户 "{user_name}" 失败！')

    def open_settings(self):
        """打开设置窗口"""
        self.settings_window = SettingsManager(
            table_viewer=self.table_viewer, 
            config_manager=self.config_manager,
            main_app=self.app
        )
        # 连接字体变化信号
        self.settings_window.font_changed.connect(self.apply_font_preview)
        self.settings_window.font_restored.connect(self.restore_original_font)
        self.settings_window.show()

    def open_visit_input_dialog(self):
        """打开就诊信息录入弹窗"""
        # 检查是否选择了用户
        current_user = self.user_combo.currentText()
        if current_user == '请选择用户...':
            QMessageBox.warning(self, '警告', '请先选择用户！')
            return
        
        # 创建并显示弹窗，传递共享的data_storage依赖
        dialog = VisitRecordDialog(current_user, self, data_storage=self.data_storage)
        dialog.record_uploaded.connect(self.on_record_uploaded)  # 连接信号
        dialog.show()
    
    def on_record_uploaded(self):
        """当记录上传成功时的回调"""
        # 刷新表格查看器的数据
        if hasattr(self, 'table_viewer'):
            self.table_viewer.load_data()
        print("记录上传成功，主窗口收到通知")

    def on_user_changed(self):
        # 保存当前用户选择
        current_user = self.user_combo.currentText()
        if current_user and current_user != '请选择用户...':
            self.config_manager.save_last_user(current_user)
        
        # 更新表格查看器的用户
        if hasattr(self, 'table_viewer'):
            self.table_viewer.set_user(current_user)
    
    def apply_font_preview(self, font_scale):
        """应用字体预览"""
        if self.app:
            font = self.app.font()
            original_point_size = font.pointSize()
            if original_point_size > 0:
                # 计算新字体大小（基于系统默认字体大小）
                # 需要恢复到基本字体大小，然后应用新的倍数
                base_point_size = getattr(self, '_base_font_size', None)
                if base_point_size is None:
                    # 第一次调用，保存基本字体大小
                    current_scale = self.config_manager.get_font_scale()
                    self._base_font_size = int(original_point_size / current_scale)
                    base_point_size = self._base_font_size
                
                new_point_size = int(base_point_size * font_scale)
                font.setPointSize(new_point_size)
                self.app.setFont(font)
    
    def restore_original_font(self):
        """恢复原始字体设置"""
        original_scale = self.config_manager.get_font_scale()
        self.apply_font_preview(original_scale)


def main():
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon('icon.png'))
    
    # 应用字体倍数设置
    config_manager = ConfigManager()
    font_scale = config_manager.get_font_scale()
    
    # 获取当前字体并应用倍数
    font = app.font()
    original_point_size = font.pointSize()
    if original_point_size > 0:
        new_point_size = int(original_point_size * font_scale)
        font.setPointSize(new_point_size)
        app.setFont(font)
    
    widget = VisitInputWidget(app=app, config_manager=config_manager)
    widget.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()