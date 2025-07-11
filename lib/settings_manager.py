from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, 
    QVBoxLayout, QHBoxLayout, QMessageBox, QSlider, QFrame
)
from PyQt6.QtCore import Qt
from .config_manager import ConfigManager
import sys

class SettingsManager(QWidget):
    def __init__(self, table_viewer=None, config_manager=None):
        super().__init__()
        self.table_viewer = table_viewer
        self.config_manager = config_manager or ConfigManager()
        self.setWindowTitle('设置管理')
        self.setFixedSize(400, 250)  # 增加高度以容纳新按钮
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 字体大小设置
        font_label = QLabel('字体大小倍数:')
        self.font_scale_edit = QLineEdit()
        self.font_scale_edit.setPlaceholderText('输入1.0-2.0之间的数值')
        
        # 滑块控制
        self.font_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_scale_slider.setMinimum(50)  # 0.5 * 100
        self.font_scale_slider.setMaximum(200)  # 2.0 * 100
        self.font_scale_slider.setValue(120)  # 默认1.2
        
        # 当前值显示
        self.current_value_label = QLabel('当前值: 1.2')
        
        # 按钮
        save_btn = QPushButton('保存设置')
        save_btn.clicked.connect(self.save_settings)
        
        reset_btn = QPushButton('重置为默认值')
        reset_btn.clicked.connect(self.reset_to_default)
        
        # 恢复默认列宽按钮
        reset_column_width_btn = QPushButton('恢复默认列宽')
        reset_column_width_btn.clicked.connect(self.reset_column_widths)
        
        # 布局
        font_layout = QHBoxLayout()
        font_layout.addWidget(font_label)
        font_layout.addWidget(self.font_scale_edit)
        
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel('0.5'))
        slider_layout.addWidget(self.font_scale_slider)
        slider_layout.addWidget(QLabel('2.0'))
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        
        # 创建分割线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("color: gray;")
        
        # 单独一行放置恢复默认列宽按钮
        column_width_layout = QHBoxLayout()
        column_width_layout.addWidget(reset_column_width_btn)
        
        layout.addLayout(font_layout)
        layout.addWidget(self.current_value_label)
        layout.addLayout(slider_layout)
        layout.addLayout(btn_layout)
        layout.addSpacing(10)  # 分割线上方间距
        layout.addWidget(separator)  # 添加分割线
        layout.addSpacing(10)  # 分割线下方间距
        layout.addLayout(column_width_layout)
        layout.addStretch()
        
        # 连接信号
        self.font_scale_edit.textChanged.connect(self.on_text_changed)
        self.font_scale_slider.valueChanged.connect(self.on_slider_changed)
        
        self.setLayout(layout)

    def load_current_settings(self):
        """加载当前设置"""
        font_scale = self.config_manager.get_font_scale()
        self.font_scale_edit.setText(str(font_scale))
        self.font_scale_slider.setValue(int(font_scale * 100))
        self.update_current_value_label()

    def on_text_changed(self):
        """文本输入框变化时的处理"""
        try:
            value = float(self.font_scale_edit.text())
            if 0.5 <= value <= 2.0:
                self.font_scale_slider.setValue(int(value * 100))
                self.update_current_value_label()
        except ValueError:
            pass

    def on_slider_changed(self):
        """滑块变化时的处理"""
        value = self.font_scale_slider.value() / 100.0
        self.font_scale_edit.setText(f"{value:.1f}")
        self.update_current_value_label()

    def update_current_value_label(self):
        """更新当前值显示"""
        try:
            value = float(self.font_scale_edit.text())
            self.current_value_label.setText(f'当前值: {value:.1f}')
        except ValueError:
            self.current_value_label.setText('当前值: 无效')

    def save_settings(self):
        """保存设置"""
        try:
            font_scale = float(self.font_scale_edit.text())
            if not (0.5 <= font_scale <= 2.0):
                QMessageBox.warning(self, '警告', '字体大小倍数必须在0.5到2.0之间！')
                return
            
            self.config_manager.save_font_scale(font_scale)
            QMessageBox.information(self, '成功', '设置已保存！重启应用程序后生效。')
            
        except ValueError:
            QMessageBox.warning(self, '错误', '请输入有效的数字！')

    def reset_to_default(self):
        """重置为默认值"""
        self.font_scale_edit.setText('1.2')
        self.font_scale_slider.setValue(120)
        self.update_current_value_label()
    
    def reset_column_widths(self):
        """恢复默认列宽"""
        if self.table_viewer:
            self.table_viewer.reset_to_default_column_widths()
            QMessageBox.information(self, '成功', '已恢复默认列宽设置！')
        else:
            QMessageBox.warning(self, '错误', '无法访问表格视图！')

def show_settings_manager():
    """显示设置管理器"""
    app = QApplication(sys.argv)
    window = SettingsManager()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    show_settings_manager() 