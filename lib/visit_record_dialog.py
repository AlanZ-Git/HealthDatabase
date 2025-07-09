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
    
    def __init__(self, user_name, parent=None, edit_record=None):
        super().__init__(parent)
        self.user_name = user_name
        self.edit_record = edit_record  # 编辑模式下的原始记录数据
        self.is_edit_mode = edit_record is not None
        self.data_storage = DataStorage()
        
        # 跟踪数据是否被修改
        self.has_unsaved_changes = False
        self.original_data = {}  # 存储原始数据用于比较
        self.force_close = False  # 标志位，用于避免重复弹出确认对话框
        
        if self.is_edit_mode:
            self.setWindowTitle('修改就诊信息')
        else:
            self.setWindowTitle('就诊信息')
        
        self.setModal(True)  # 设置为模态对话框
        self.init_ui()
        
        # 如果是编辑模式，预填数据
        if self.is_edit_mode:
            self.populate_edit_data()
        
        # 保存初始数据状态
        self.save_original_data()
        
        # 连接所有输入控件的信号来检测变化
        self.connect_change_signals()
        
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
        
        # 根据模式设置按钮文本
        if self.is_edit_mode:
            self.upload_btn = QPushButton('保存修改')
        else:
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

        # 时间信息显示区（仅在编辑模式下显示）
        time_info_layout = QHBoxLayout()
        if self.is_edit_mode:
            self.created_time_label = QLabel()
            self.updated_time_label = QLabel()
            self.created_time_label.setStyleSheet("color: #666; font-size: 11px;")
            self.updated_time_label.setStyleSheet("color: #666; font-size: 11px;")
            time_info_layout.addWidget(self.created_time_label)
            time_info_layout.addStretch()
            time_info_layout.addWidget(self.updated_time_label)

        # 底部按钮区
        bottom_btn_h = QHBoxLayout()
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.close_with_confirmation)
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
        
        # 添加时间信息布局（仅在编辑模式下）
        if self.is_edit_mode:
            main_layout.addSpacing(10)
            main_layout.addLayout(time_info_layout)
        
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

    def save_original_data(self):
        """保存当前表单数据作为原始数据，用于比较是否有修改"""
        self.original_data = {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'hospital': self.hospital_edit.text().strip(),
            'department': self.department_edit.text().strip(),
            'doctor': self.doctor_edit.text().strip(),
            'organ_system': self.organ_system_edit.text().strip(),
            'reason': self.reason_edit.toPlainText().strip(),
            'diagnosis': self.diagnosis_edit.toPlainText().strip(),
            'medication': self.medication_edit.toPlainText().strip(),
            'remark': self.remark_edit.toPlainText().strip(),
        }

    def connect_change_signals(self):
        """连接所有输入控件的信号来检测数据变化"""
        self.date_edit.dateChanged.connect(self.on_data_changed)
        self.hospital_edit.textChanged.connect(self.on_data_changed)
        self.department_edit.textChanged.connect(self.on_data_changed)
        self.doctor_edit.textChanged.connect(self.on_data_changed)
        self.organ_system_edit.textChanged.connect(self.on_data_changed)
        self.reason_edit.textChanged.connect(self.on_data_changed)
        self.diagnosis_edit.textChanged.connect(self.on_data_changed)
        self.medication_edit.textChanged.connect(self.on_data_changed)
        self.remark_edit.textChanged.connect(self.on_data_changed)
        self.attachment_list.itemChanged.connect(self.on_data_changed)

    def on_data_changed(self):
        """数据改变时的处理函数"""
        # 获取当前数据
        current_data = {
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'hospital': self.hospital_edit.text().strip(),
            'department': self.department_edit.text().strip(),
            'doctor': self.doctor_edit.text().strip(),
            'organ_system': self.organ_system_edit.text().strip(),
            'reason': self.reason_edit.toPlainText().strip(),
            'diagnosis': self.diagnosis_edit.toPlainText().strip(),
            'medication': self.medication_edit.toPlainText().strip(),
            'remark': self.remark_edit.toPlainText().strip(),
        }
        
        # 比较当前数据与原始数据
        self.has_unsaved_changes = current_data != self.original_data

    def close_with_confirmation(self):
        """带确认的关闭方法"""
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, 
                '确认关闭', 
                '您有未保存的修改，确定要放弃修改并关闭窗口吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.force_close = True  # 设置强制关闭标志
                self.close()
        else:
            self.close()

    def closeEvent(self, event):
        """重写关闭事件，检查未保存的修改"""
        # 如果是强制关闭，直接关闭
        if self.force_close:
            event.accept()
            return
            
        if self.has_unsaved_changes:
            reply = QMessageBox.question(
                self, 
                '确认关闭', 
                '您有未保存的修改，确定要放弃修改并关闭窗口吗？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def upload_visit_record(self):
        """上传本次就诊记录或更新记录"""
        # 收集表单数据并整理成数据库字段字典
        visit_data = self._collect_visit_data()
        
        # 在编辑模式下添加记录ID
        if self.is_edit_mode:
            visit_data['visit_record_id'] = self.edit_record.get('visit_record_id')
        
        # 显示收集到的数据（调试用）
        mode_text = "修改" if self.is_edit_mode else "新增"
        print(f"=== 收集到的就诊记录数据（{mode_text}）===")
        for key, value in visit_data.items():
            print(f"{key}: {value!r}")
        print("================================")
        
        # 调用对应的data_storage方法
        try:
            if self.is_edit_mode:
                success = self.data_storage.update_visit_record(visit_data)
                success_msg = '就诊记录修改成功！'
                error_msg = '就诊记录修改失败！请检查数据格式和数据库连接。'
            else:
                success = self.data_storage.upload_visit_record(visit_data)
                success_msg = '就诊记录上传成功！'
                error_msg = '就诊记录上传失败！请检查数据格式和数据库连接。'
            
            if success:
                QMessageBox.information(self, '成功', success_msg)
                # 发出信号通知主窗口
                self.record_uploaded.emit()
                
                # 重置修改标志，因为数据已保存
                self.has_unsaved_changes = False
                self.save_original_data()
                
                if self.is_edit_mode:
                    # 编辑模式下成功后关闭对话框
                    self.force_close = True  # 设置强制关闭标志
                    self.close()
                else:
                    # 新增模式下清空表单，但保持就诊日期不变
                    self._clear_form_after_upload()
                    # 重新保存原始数据状态
                    self.save_original_data()
            else:
                QMessageBox.warning(self, '错误', error_msg)
                
        except Exception as e:
            operation = "修改" if self.is_edit_mode else "上传"
            print(f"{operation}记录时发生错误: {e}")
            QMessageBox.critical(self, '错误', f'{operation}记录时发生错误：\n{str(e)}')

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

    def populate_edit_data(self):
        """在编辑模式下预填数据"""
        if not self.edit_record:
            return
        
        # 预填基本信息
        date_str = self.edit_record.get('date', '')
        if date_str:
            date = QDate.fromString(date_str, "yyyy-MM-dd")
            if date.isValid():
                self.date_edit.setDate(date)
        
        self.hospital_edit.setText(self.edit_record.get('hospital', '') or '')
        self.department_edit.setText(self.edit_record.get('department', '') or '')
        self.doctor_edit.setText(self.edit_record.get('doctor', '') or '')
        self.organ_system_edit.setText(self.edit_record.get('organ_system', '') or '')
        self.reason_edit.setPlainText(self.edit_record.get('reason', '') or '')
        self.diagnosis_edit.setPlainText(self.edit_record.get('diagnosis', '') or '')
        self.medication_edit.setPlainText(self.edit_record.get('medication', '') or '')
        self.remark_edit.setPlainText(self.edit_record.get('remark', '') or '')
        
        # 设置时间显示
        created_at = self.edit_record.get('created_at', '')
        updated_at = self.edit_record.get('updated_at', '')
        
        if created_at:
            self.created_time_label.setText(f"创建时间：{created_at}")
        if updated_at:
            self.updated_time_label.setText(f"更新时间：{updated_at}") 