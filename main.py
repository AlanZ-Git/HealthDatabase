from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, 
    QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QTabWidget,
    QComboBox, QMessageBox, QInputDialog
)

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
import configparser
import os

from lib.data_storage import DataStorage
from lib.settings_manager import SettingsManager
from lib.visit_record_dialog import VisitRecordDialog

def load_settings():
    """加载设置文件"""
    config = configparser.ConfigParser()
    settings_file = 'settings.ini'
    
    # 如果设置文件不存在，创建默认设置
    if not os.path.exists(settings_file):
        config['Display'] = {'font_scale': '1.2'}
        with open(settings_file, 'w', encoding='utf-8') as f:
            config.write(f)
    else:
        config.read(settings_file, encoding='utf-8')
    
    # 获取字体缩放倍数，默认为1.2
    try:
        font_scale = float(config.get('Display', 'font_scale', fallback='1.2'))
    except (ValueError, configparser.Error):
        font_scale = 1.2
    
    return font_scale

def apply_global_font_scale(app, font_scale):
    """应用全局字体缩放"""
    # 获取当前字体
    current_font = app.font()
    
    # 计算新的字体大小
    new_size = int(current_font.pointSize() * font_scale)
    
    # 创建新字体
    new_font = QFont(current_font.family(), new_size)
    new_font.setBold(current_font.bold())
    new_font.setItalic(current_font.italic())
    
    # 应用新字体
    app.setFont(new_font)

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
        # 设置按钮宽度和创建新用户按钮一样
        self.settings_btn.setFixedWidth(100)  # 设置固定宽度，与创建新用户按钮保持一致
        
        # 读取data文件夹下的sqlite文件
        self.load_users()
        # 加载上次选择的用户
        self.load_last_user()
        
        # 录入就诊信息按钮
        self.visit_input_btn = QPushButton('录入就诊信息')
        self.visit_input_btn.clicked.connect(self.open_visit_input_dialog)
        self.visit_input_btn.setFixedWidth(100)
        
        # 创建竖向分隔符
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        
        # 用户选择布局
        user_grid = QGridLayout()
        user_grid.setSpacing(6)
        user_grid.addWidget(user_label, 0, 0)
        user_grid.addWidget(self.user_combo, 0, 1)
        user_grid.addWidget(self.create_user_btn, 0, 2)
        user_grid.addWidget(self.delete_user_btn, 0, 3)
        user_grid.addWidget(separator, 0, 4)
        user_grid.addWidget(self.visit_input_btn, 0, 5)
        user_grid.setColumnStretch(6, 1)  # 中间区域拉伸
        user_grid.addWidget(self.settings_btn, 0, 7)  # 设置按钮单独放在最右端

        # 顶部Tab
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_export_tab(), '就诊情况导出标签页')

        main_layout = QVBoxLayout()
        main_layout.addLayout(user_grid)  # 用户选择在最上方
        main_layout.addSpacing(10)  # 添加一些间距
        main_layout.addWidget(self.tabs)  # Tab控件在下方
        self.setLayout(main_layout)
        self.resize(1200, 700)



    def _create_export_tab(self):
        # 伪代码+注释占位
        tab = QWidget()
        layout = QVBoxLayout()
        label = QLabel('此处为"就诊情况导出"功能区，待后续实现...')
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        # TODO: 这里将来实现导出相关功能
        tab.setLayout(layout)
        return tab



    def load_users(self):
        """读取data文件夹下的sqlite文件作为用户列表"""
        # 清空现有项目（保留第一个"请选择用户..."）
        while self.user_combo.count() > 1:
            self.user_combo.removeItem(1)
        
        # 使用data_storage获取所有用户
        users = self.data_storage.get_all_users()
        for user_name in users:
            self.user_combo.addItem(user_name)

    def create_new_user(self):
        """创建新用户"""
        user_name, ok = QInputDialog.getText(self, '创建新用户', '请输入用户名:')
        if ok and user_name.strip():
            user_name = user_name.strip()
            
            # 使用data_storage创建用户
            if self.data_storage.create_user(user_name):
                # 添加到下拉框
                self.user_combo.addItem(user_name)
                self.user_combo.setCurrentText(user_name)
                QMessageBox.information(self, '成功', f'用户 "{user_name}" 创建成功！')
            else:
                QMessageBox.warning(self, '警告', '用户名已存在！')

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
        self.settings_window = SettingsManager()
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
        # 这里可以添加一些响应逻辑，比如刷新某些数据
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



    def load_last_user(self):
        import configparser
        config = configparser.ConfigParser()
        history_file = 'history.ini'
        last_user = None
        if os.path.exists(history_file):
            config.read(history_file, encoding='utf-8')
            last_user = config.get('History', 'last_user', fallback=None)
        if last_user and self.user_combo.findText(last_user) != -1:
            self.user_combo.setCurrentText(last_user)
        elif self.user_combo.count() == 1:
            self.user_combo.setCurrentText('请创建新用户')

def show_ui():
    app = QApplication(sys.argv)
    
    # 加载设置并应用全局字体缩放
    font_scale = load_settings()
    apply_global_font_scale(app, font_scale)
    
    window = VisitInputWidget()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    show_ui()