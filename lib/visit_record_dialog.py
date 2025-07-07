from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFileDialog, QFrame, QSizePolicy,
    QListWidgetItem, QCheckBox, QDateEdit, QCompleter, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QFont
import os

from .data_storage import DataStorage

class VisitRecordDialog(QDialog):
    """就诊信息录入弹窗"""
    
    # 定义信号，当记录上传成功时发出
    record_uploaded = pyqtSignal()
    
    def __init__(self, user_name, parent=None):
        super().__init__(parent)
        self.user_name = user_name
        self.data_storage = DataStorage()
        self.setWindowTitle('就诊信息')
        self.setModal(True)  # 设置为模态对话框
        self.init_ui()
        self.resize(1000, 600)

    def init_ui(self):
        """初始化UI"""
        # 显示当前用户
        user_info_label = QLabel(f'当前用户：{self.user_name}')
        user_info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        
        # 就诊日期、医院名称、科室名称、医生名称
        date_label = QLabel('就诊日期')
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
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
        self.hospital_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.hospital_edit.setCompleter(self.hospital_completer)
        self.hospital_edit.textChanged.connect(self.update_hospital_completer)
        # 初始化自动完成列表
        self.update_hospital_completer()
        
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
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setFrameShadow(QFrame.Shadow.Sunken)

        # 器官系统、诊断结果、用药信息、备注、症状事由
        self.organ_system_edit = QLineEdit()
        self.organ_system_edit.setPlaceholderText('器官系统输入框')
        self.diagnosis_edit = QTextEdit()
        self.diagnosis_edit.setPlaceholderText('诊断结果输入框')
        self.medication_edit = QTextEdit()
        self.medication_edit.setPlaceholderText('用药信息输入框')
        self.remark_edit = QTextEdit()
        self.remark_edit.setPlaceholderText('备注输入框')
        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText('症状事由输入框')

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
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setFrameShadow(QFrame.Shadow.Sunken)

        # 附件按钮区（横向）
        self.add_attachment_btn = QPushButton('添加附件按钮')
        self.remove_attachment_btn = QPushButton('移除附件按钮')
        self.remove_all_attachment_btn = QPushButton('移除所有附件按钮')
        self.upload_btn = QPushButton('上传本次记录按钮')
        
        self.upload_btn.clicked.connect(self.upload_visit_record)
        self.add_attachment_btn.clicked.connect(self.add_attachment)
        self.remove_attachment_btn.clicked.connect(self.remove_attachment)
        self.remove_all_attachment_btn.clicked.connect(self.remove_all_attachment)
        
        attach_btn_h = QHBoxLayout()
        attach_btn_h.addWidget(self.add_attachment_btn)
        attach_btn_h.addWidget(self.remove_attachment_btn)
        attach_btn_h.addWidget(self.remove_all_attachment_btn)
        attach_btn_h.addStretch()
        attach_btn_h.addWidget(self.upload_btn)

        # 附件展示区
        self.attachment_list = QListWidget()
        self.attachment_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        self.attachment_list.itemChanged.connect(self._update_placeholder)
        self._update_placeholder()

        attach_v = QVBoxLayout()
        attach_v.addWidget(QLabel('附件'))
        attach_v.addLayout(attach_btn_h)
        attach_v.addWidget(self.attachment_list)

        # 底部按钮区
        bottom_btn_h = QHBoxLayout()
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close)
        bottom_btn_h.addStretch()
        bottom_btn_h.addWidget(close_btn)

        # 主体布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(user_info_label)
        main_layout.addLayout(grid_top)
        main_layout.addWidget(line1)
        main_layout.addLayout(input_h)
        main_layout.addWidget(line2)
        main_layout.addLayout(attach_v)
        main_layout.addSpacing(10)
        main_layout.addLayout(bottom_btn_h)
        main_layout.setSpacing(12)
        
        self.setLayout(main_layout)

    def add_attachment(self):
        """添加附件"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择附件')
        if file_paths:
            for file_path in file_paths:
                item = QListWidgetItem()
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                self.attachment_list.addItem(item)
                self.attachment_list.setItemWidget(item, checkbox)
                item.setData(Qt.ItemDataRole.UserRole, file_path)
                checkbox.setText(file_path)
            self._update_placeholder()

    def remove_attachment(self):
        """移除选中的附件"""
        items_to_remove = []
        for i in range(self.attachment_list.count()):
            item = self.attachment_list.item(i)
            checkbox = self.attachment_list.itemWidget(item)
            if checkbox and checkbox.isChecked():
                items_to_remove.append(i)
        
        for i in reversed(items_to_remove):
            self.attachment_list.takeItem(i)
        self._update_placeholder()

    def remove_all_attachment(self):
        """移除所有附件"""
        self.attachment_list.clear()
        self._update_placeholder()

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
            placeholder_item = QListWidgetItem("附件展示区")
            placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder_item.setForeground(Qt.GlobalColor.gray)
            self.attachment_list.addItem(placeholder_item)
        else:
            for i in range(self.attachment_list.count()):
                item = self.attachment_list.item(i)
                if item.text() == "附件展示区" and item.flags() == Qt.ItemFlag.NoItemFlags:
                    self.attachment_list.takeItem(i)
                    break

    def update_hospital_completer(self):
        """更新医院名称自动完成列表"""
        # 获取历史医院名称
        history_hospitals = self.data_storage.get_history_hospitals(self.user_name, limit=20)
        
        # 获取当前输入内容
        current_text = self.hospital_edit.text().strip()
        
        # 根据输入内容过滤医院名称
        if current_text:
            filtered_hospitals = [hospital for hospital in history_hospitals 
                                if current_text.lower() in hospital.lower()]
        else:
            filtered_hospitals = history_hospitals[:5]
        
        # 更新自动完成列表
        self.hospital_completer.setModel(None)
        if filtered_hospitals:
            from PyQt6.QtCore import QStringListModel
            model = QStringListModel(filtered_hospitals)
            self.hospital_completer.setModel(model)

    def _clear_form_after_upload(self):
        """上传记录后清空表单，但保持就诊日期不变"""
        current_date = self.date_edit.date()
        
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
        
        self.date_edit.setDate(current_date)

    def upload_visit_record(self):
        """上传本次就诊记录"""
        # 收集表单数据并整理成数据库字段字典
        visit_data = self._collect_visit_data()
        
        # 显示收集到的数据（调试用）
        print("=== 收集到的就诊记录数据 ===")
        for key, value in visit_data.items():
            print(f"{key}: {value!r}")
        print("================================")
        
        # 调用data_storage模块上传记录
        try:
            success = self.data_storage.upload_visit_record(visit_data)
            
            if success:
                QMessageBox.information(self, '成功', '就诊记录上传成功！')
                # 发出信号通知主窗口
                self.record_uploaded.emit()
                # 上传成功后清空表单，但保持就诊日期不变
                self._clear_form_after_upload()
            else:
                QMessageBox.warning(self, '错误', '就诊记录上传失败！请检查数据格式和数据库连接。')
                
        except Exception as e:
            print(f"上传记录时发生错误: {e}")
            QMessageBox.critical(self, '错误', f'上传记录时发生错误：\n{str(e)}')

    def _collect_visit_data(self) -> dict:
        """
        收集当前表单的所有数据并整理成数据库字段字典
        
        Returns:
            包含所有表单数据的字典，字段对应数据库表结构
        """
        # 获取所有附件文件路径
        attachment_paths = []
        for i in range(self.attachment_list.count()):
            item = self.attachment_list.item(i)
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path:
                attachment_paths.append(file_path)
        
        # 整理数据成数据库字段格式
        visit_data = {
            'user_name': self.user_name,
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'hospital': self.hospital_edit.text().strip(),
            'department': self.department_edit.text().strip(),
            'doctor': self.doctor_edit.text().strip(),
            'organ_system': self.organ_system_edit.text().strip(),
            'reason': self.reason_edit.toPlainText().strip(),
            'diagnosis': self.diagnosis_edit.toPlainText().strip(),
            'medication': self.medication_edit.toPlainText().strip(),
            'remark': self.remark_edit.toPlainText().strip(),
            'attachment_paths': attachment_paths
        }
        
        return visit_data

    def get_data(self):
        """获取表单数据（兼容性方法）"""
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
            'attachment': [self.attachment_list.item(i).data(Qt.ItemDataRole.UserRole) 
                          for i in range(self.attachment_list.count())]
        } 