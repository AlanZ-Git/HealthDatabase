from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFileDialog, QFrame, QSizePolicy, QTabWidget,
    QListWidgetItem, QCheckBox, QComboBox, QDateEdit, QCompleter
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
import sys
import configparser
import os

from lib.data_storage import DataStorage
from lib.settings_manager import SettingsManager

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
        
        # 用户选择布局
        user_grid = QGridLayout()
        user_grid.setSpacing(6)
        user_grid.addWidget(user_label, 0, 0)
        user_grid.addWidget(self.user_combo, 0, 1)
        user_grid.addWidget(self.create_user_btn, 0, 2)
        user_grid.addWidget(self.delete_user_btn, 0, 3)
        user_grid.setColumnStretch(4, 1)  # 中间区域拉伸
        user_grid.addWidget(self.settings_btn, 0, 5)  # 设置按钮单独放在最右端

        # 顶部Tab
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_input_tab(), '就诊情况录入标签页')
        self.tabs.addTab(self._create_export_tab(), '就诊情况导出标签页')

        main_layout = QVBoxLayout()
        main_layout.addLayout(user_grid)  # 用户选择在最上方
        main_layout.addSpacing(10)  # 添加一些间距
        main_layout.addWidget(self.tabs)  # Tab控件在下方
        self.setLayout(main_layout)
        self.resize(1200, 700)

    def _create_input_tab(self):
        # 录入页内容（原main_layout）
        tab = QWidget()
        # 第二排：就诊日期、医院名称、科室名称、医生名称
        date_label = QLabel('就诊日期')
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)  # 允许弹出日历选择
        self.date_edit.setDisplayFormat("yyyy-MM-dd")  # 设置日期显示格式
        self.date_edit.setDate(QDate.currentDate())  # 设置默认日期为当前日期
        self.date_edit.setMinimumWidth(208)

        date_hbox = QHBoxLayout()
        date_hbox.setSpacing(6)
        date_hbox.addWidget(date_label)
        date_hbox.addWidget(self.date_edit)
        date_hbox.addStretch()

        hospital_label = QLabel('医院名称')
        self.hospital_edit = QLineEdit()
        self.hospital_edit.setPlaceholderText('医院名称输入框')
        self.hospital_edit.setMinimumWidth(208)
        # 为医院名称输入框添加自动完成功能
        self.hospital_completer = QCompleter()
        self.hospital_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)  # 不区分大小写
        self.hospital_edit.setCompleter(self.hospital_completer)
        # 当用户开始输入时更新自动完成列表
        self.hospital_edit.textChanged.connect(self.update_hospital_completer)
        hospital_hbox = QHBoxLayout()
        hospital_hbox.setSpacing(6)
        hospital_hbox.addWidget(hospital_label)
        hospital_hbox.addWidget(self.hospital_edit)
        hospital_hbox.addStretch()

        department_label = QLabel('科室名称')
        self.department_edit = QLineEdit()
        self.department_edit.setPlaceholderText('科室名称输入框')
        self.department_edit.setMinimumWidth(208)
        department_hbox = QHBoxLayout()
        department_hbox.setSpacing(6)
        department_hbox.addWidget(department_label)
        department_hbox.addWidget(self.department_edit)
        department_hbox.addStretch()

        doctor_label = QLabel('医生名称')
        self.doctor_edit = QLineEdit()
        self.doctor_edit.setPlaceholderText('医生名称输入框')
        self.doctor_edit.setMinimumWidth(208)
        doctor_hbox = QHBoxLayout()
        doctor_hbox.setSpacing(6)
        doctor_hbox.addWidget(doctor_label)
        doctor_hbox.addWidget(self.doctor_edit)
        doctor_hbox.addStretch()

        grid_top = QGridLayout()
        grid_top.addLayout(date_hbox, 0, 0)
        grid_top.addLayout(hospital_hbox, 0, 1)
        grid_top.addLayout(department_hbox, 0, 2)
        grid_top.addLayout(doctor_hbox, 0, 3)
        for i in range(4):
            grid_top.setColumnStretch(i, 1)
        # 分割线1
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setFrameShadow(QFrame.Shadow.Sunken)
        # 第二排：器官系统、诊断结果、用药信息、备注、症状事由
        self.organ_system_edit = QLineEdit(); self.organ_system_edit.setPlaceholderText('器官系统输入框')
        self.diagnosis_edit = QTextEdit(); self.diagnosis_edit.setPlaceholderText('诊断结果输入框')
        self.medication_edit = QTextEdit(); self.medication_edit.setPlaceholderText('用药信息输入框')
        self.remark_edit = QTextEdit(); self.remark_edit.setPlaceholderText('备注输入框')
        self.reason_edit = QTextEdit(); self.reason_edit.setPlaceholderText('症状事由输入框')
        # 左侧：器官系统+症状事由
        left_v = QVBoxLayout()
        left_v.addWidget(QLabel('器官系统'))
        left_v.addWidget(self.organ_system_edit)
        left_v.addWidget(QLabel('症状事由'))
        left_v.addWidget(self.reason_edit)
        # 中间：诊断结果
        center_v = QVBoxLayout()
        center_v.addWidget(QLabel('诊断结果'))
        center_v.addWidget(self.diagnosis_edit)
        # 右中：用药信息
        med_v = QVBoxLayout()
        med_v.addWidget(QLabel('用药信息'))
        med_v.addWidget(self.medication_edit)
        # 右侧：备注
        remark_v = QVBoxLayout()
        remark_v.addWidget(QLabel('备注'))
        remark_v.addWidget(self.remark_edit)
        # 水平排列
        input_h = QHBoxLayout()
        input_h.addLayout(left_v, 2)
        input_h.addSpacing(10)
        input_h.addLayout(center_v, 2)
        input_h.addSpacing(10)
        input_h.addLayout(med_v, 2)
        input_h.addSpacing(10)
        input_h.addLayout(remark_v, 2)
        # 分割线2
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.HLine); line2.setFrameShadow(QFrame.Shadow.Sunken)
        # 附件按钮区（横向）
        self.add_attachment_btn = QPushButton('添加附件按钮')
        self.remove_attachment_btn = QPushButton('移除附件按钮')
        self.remove_all_attachment_btn = QPushButton('移除所有附件按钮')
        self.upload_btn = QPushButton('上传本次记录按钮')
        self.add_attachment_btn.clicked.connect(self.add_attachment)
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        self.remove_all_attachment_btn.clicked.connect(self.remove_all_attachment)
        self.upload_btn.clicked.connect(self.upload_record)
        attach_btn_h = QHBoxLayout()
        attach_btn_h.addWidget(self.add_attachment_btn)
        attach_btn_h.addWidget(self.remove_attachment_btn)
        attach_btn_h.addWidget(self.remove_all_attachment_btn)
        attach_btn_h.addStretch()
        attach_btn_h.addWidget(self.upload_btn)  # 上传按钮右对齐到附件展示区
        # 附件展示区
        self.attachment_list = QListWidget()
        self.attachment_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # 设置边框样式，参考输入框的细边框
        self.attachment_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #c0c0c0;
                background-color: #ffffff;
                padding: 2px;
            }
            QListWidget::item {
                padding: 3px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #0078d4;
                color: #ffffff;
            }
        """)
        # 为QListWidget添加占位符效果
        self.attachment_list.itemChanged.connect(self._update_placeholder)
        self._update_placeholder()
        attach_v = QVBoxLayout()
        attach_v.addWidget(QLabel('附件'))
        attach_v.addLayout(attach_btn_h)
        attach_v.addWidget(self.attachment_list)
        # 附件区布局（移除右侧按钮区）
        bottom_h = QHBoxLayout()
        bottom_h.addLayout(attach_v)
        # 主体竖直布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(grid_top)
        main_layout.addWidget(line1)
        main_layout.addLayout(input_h)
        main_layout.addWidget(line2)
        main_layout.addLayout(bottom_h)
        main_layout.setSpacing(12)
        tab.setLayout(main_layout)
        return tab

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

    def add_attachment(self):
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择附件')
        if file_paths:
            for file_path in file_paths:
                # 创建带勾选框的列表项
                item = QListWidgetItem()
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                self.attachment_list.addItem(item)
                self.attachment_list.setItemWidget(item, checkbox)
                # 将文件路径存储在item的data中
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                # 设置显示文本为文件路径
                checkbox.setText(file_path)
            self._update_placeholder()

    def remove_attachment(self):
        # 移除所有勾选的附件
        items_to_remove = []
        for i in range(self.attachment_list.count()):
            item = self.attachment_list.item(i)
            checkbox = self.attachment_list.itemWidget(item)
            if checkbox and checkbox.isChecked():
                items_to_remove.append(i)
        
        # 从后往前移除，避免索引变化
        for i in reversed(items_to_remove):
            self.attachment_list.takeItem(i)
        self._update_placeholder()

    def remove_all_attachment(self):
        self.attachment_list.clear()
        self._update_placeholder()

    def upload_record(self):
        """上传本次记录"""
        from PyQt6.QtWidgets import QMessageBox
        
        # 检查是否选择了用户
        current_user = self.user_combo.currentText()
        if current_user == '请选择用户...':
            QMessageBox.warning(self, '警告', '请先选择用户！')
            return
        
        # 获取表单数据
        data = self.get_data()
        
        # 检查必填字段
        if not data['hospital'].strip():
            QMessageBox.warning(self, '警告', '请填写医院名称！')
            return
        
        # 使用data_storage保存记录
        if self.data_storage.save_visit_record(current_user, data):
            QMessageBox.information(self, '成功', '就诊记录保存成功！')
            # 清空表单
            self.clear_form()
        else:
            QMessageBox.warning(self, '错误', '保存就诊记录失败！')

    def clear_form(self):
        """清空表单"""
        self.date_edit.setDate(QDate.currentDate())
        self.hospital_edit.clear()
        self.department_edit.clear()
        self.doctor_edit.clear()
        self.organ_system_edit.clear()
        self.reason_edit.clear()
        self.diagnosis_edit.clear()
        self.medication_edit.clear()
        self.remark_edit.clear()
        self.attachment_list.clear()
        self._update_placeholder()

    def _update_placeholder(self):
        """更新附件列表的占位符显示"""
        if self.attachment_list.count() == 0:
            # 当列表为空时，添加一个占位符项
            placeholder_item = QListWidgetItem("附件展示区")
            placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 禁用选择
            placeholder_item.setForeground(Qt.GlobalColor.gray)  # 设置为灰色
            self.attachment_list.addItem(placeholder_item)
        else:
            # 当列表有内容时，移除占位符项
            for i in range(self.attachment_list.count()):
                item = self.attachment_list.item(i)
                if item.text() == "附件展示区" and item.flags() == Qt.ItemFlag.NoItemFlags:
                    self.attachment_list.takeItem(i)
                    break

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
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
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
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        
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

    def get_data(self):
        return {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'hospital': self.hospital_edit.text(),
            'department': self.department_edit.text(),
            'doctor': self.doctor_edit.text(),
            'organ_system': self.organ_system_edit.text(),
            'reason': self.reason_edit.toPlainText(),
            'diagnosis': self.diagnosis_edit.toPlainText(),
            'medication': self.medication_edit.toPlainText(),
            'remark': self.remark_edit.toPlainText(),
            'attachment': [self.attachment_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.attachment_list.count())]
        }
    
    def update_hospital_completer(self):
        """更新医院名称自动完成列表"""
        current_user = self.user_combo.currentText()
        if current_user == '请选择用户...':
            return
        
        # 获取历史医院名称
        history_hospitals = self.data_storage.get_history_hospitals(current_user, limit=20)  # 增加查询数量以支持过滤
        
        # 获取当前输入内容
        current_text = self.hospital_edit.text().strip()
        
        # 调试信息
        print(f"当前用户: {current_user}")
        print(f"历史医院名称: {history_hospitals}")
        print(f"当前输入: '{current_text}'")
        
        # 根据输入内容过滤医院名称
        if current_text:
            # 支持模糊匹配：包含输入内容的医院名称
            filtered_hospitals = [hospital for hospital in history_hospitals 
                                if current_text.lower() in hospital.lower()]
            print(f"过滤后的医院名称: {filtered_hospitals}")
        else:
            # 如果没有输入内容，显示前5个历史医院名称
            filtered_hospitals = history_hospitals[:5]
            print(f"显示前5个历史医院名称: {filtered_hospitals}")
        
        # 更新自动完成列表
        self.hospital_completer.setModel(None)  # 清除旧模型
        if filtered_hospitals:
            from PyQt6.QtCore import QStringListModel
            model = QStringListModel(filtered_hospitals)
            self.hospital_completer.setModel(model)
            print(f"已设置自动完成模型，包含 {len(filtered_hospitals)} 个项目")
        else:
            print("没有找到匹配的医院名称")
    
    def on_user_changed(self):
        """当用户选择改变时调用"""
        # 更新医院名称自动完成列表
        self.update_hospital_completer()



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