import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QMessageBox, QInputDialog, QFrame
)
from PyQt6.QtCore import Qt
from lib.data_storage import DataStorage
from lib.table_viewer import TableViewer
from lib.visit_record_dialog import VisitRecordDialog
from lib.settings_manager import SettingsManager


class VisitInputWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('就诊记录')
        self.data_storage = DataStorage()  # 初始化数据存储管理器
        self.init_ui()

    def init_ui(self):
        # 用户选择区域
        user_label = QLabel('选择用户')
        self.user_combo = QComboBox()
        self.user_combo.addItem('请选择用户...')
        self.user_combo.setMinimumWidth(208)
        # 当用户选择改变时，更新医院名称自动完成列表
        self.user_combo.currentTextChanged.connect(self.on_user_changed)
        self.create_user_btn = QPushButton('创建新用户')
        self.create_user_btn.clicked.connect(self.create_new_user)
        self.delete_user_btn = QPushButton('删除用户')
        self.delete_user_btn.clicked.connect(self.delete_user)
        self.settings_btn = QPushButton('设置')
        self.settings_btn.clicked.connect(self.open_settings)
        self.settings_btn.setFixedWidth(80)  # 设置固定宽度，与刷新按钮保持一致
        
        # 读取data文件夹下的sqlite文件
        self.load_users()
        # 加载上次选择的用户
        self.load_last_user()
        
        # 创建竖向分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        
        # 用户选择布局
        user_layout = QHBoxLayout()
        user_layout.setSpacing(6)
        user_layout.addWidget(user_label)
        user_layout.addWidget(self.user_combo)
        user_layout.addWidget(self.create_user_btn)
        user_layout.addWidget(self.delete_user_btn)
        user_layout.addStretch()  # 中间区域拉伸，与表格查看器的布局保持一致
        user_layout.addWidget(self.settings_btn)  # 设置按钮在最右端，与刷新按钮对齐

        # 表格查看区域（直接嵌入，不使用Tab）
        self.table_viewer = TableViewer()
        # 连接信号，处理录入就诊信息的请求
        self.table_viewer.visit_input_requested.connect(self.open_visit_input_dialog)
        
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
        import configparser
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            if config.has_section('History') and config.has_option('History', 'last_user'):
                last_user = config.get('History', 'last_user')
                # 在下拉框中查找并选择该用户
                index = self.user_combo.findText(last_user)
                if index >= 0:
                    self.user_combo.setCurrentIndex(index)

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
        
        # 弹窗让用户选择要删除的用户
        user_name, ok = QInputDialog.getItem(
            self, 
            '选择要删除的用户', 
            '请选择要删除的用户:',
            users,
            0,  # 默认选择第一个
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
        self.settings_window = SettingsManager(table_viewer=self.table_viewer)
        self.settings_window.show()

    def open_visit_input_dialog(self):
        """打开就诊信息录入弹窗"""
        # 检查是否选择了用户
        current_user = self.user_combo.currentText()
        if current_user == '请选择用户...':
            QMessageBox.warning(self, '警告', '请先选择用户！')
            return
        
        # 创建并显示弹窗
        dialog = VisitRecordDialog(current_user, self)
        dialog.record_uploaded.connect(self.on_record_uploaded)  # 连接信号
        dialog.show()
    
    def on_record_uploaded(self):
        """当记录上传成功时的回调"""
        # 刷新表格查看器的数据
        if hasattr(self, 'table_viewer'):
            self.table_viewer.load_data()
        print("记录上传成功，主窗口收到通知")

    def on_user_changed(self):
        # 保存当前用户到history.ini
        current_user = self.user_combo.currentText()
        if current_user and current_user != '请选择用户...':
            import configparser
            config = configparser.ConfigParser()
            history_file = 'history.ini'
            if os.path.exists(history_file):
                config.read(history_file, encoding='utf-8')
            if 'History' not in config:
                config['History'] = {}
            config['History']['last_user'] = current_user
            with open(history_file, 'w', encoding='utf-8') as f:
                config.write(f)
        
        # 更新表格查看器的用户
        if hasattr(self, 'table_viewer'):
            self.table_viewer.set_user(current_user)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序图标（如果有的话）
    # app.setWindowIcon(QIcon('icon.png'))
    
    widget = VisitInputWidget()
    widget.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()