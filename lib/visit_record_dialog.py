from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QTextEdit, QPushButton, QListWidget,
    QHBoxLayout, QVBoxLayout, QGridLayout, QFileDialog, QFrame, QSizePolicy,
    QListWidgetItem, QCheckBox, QDateEdit, QCompleter, QMessageBox
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QStringListModel
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent
import os

from .data_storage import DataStorage
from .attachment_dialog import AttachmentDialog


class AutoCompleteLineEdit(QLineEdit):
    """带历史记录自动完成功能的输入框"""
    
    def __init__(self, placeholder_text: str = "", history_limit: int = 5, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setMinimumWidth(208)
        self.history_limit = history_limit
        self.data_fetcher = None  # 数据获取函数
        
        # 初始化自动完成器
        self._setup_completer()
        
        # 连接信号
        self.textChanged.connect(self._update_completer)
    
    def _setup_completer(self):
        """设置自动完成器"""
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.setCompleter(self.completer)
    
    def set_data_fetcher(self, fetcher_func):
        """设置数据获取函数"""
        self.data_fetcher = fetcher_func
    
    def focusInEvent(self, event):
        """获得焦点时触发自动完成"""
        super().focusInEvent(event)
        self._update_completer()
        
        # 如果输入框为空且有候选项，显示下拉列表
        if (self.completer.model() and 
            self.completer.model().rowCount() > 0 and 
            not self.text().strip()):
            self.completer.setCompletionPrefix("")
            self.completer.complete()
    
    def _update_completer(self):
        """更新自动完成列表"""
        if not self.data_fetcher:
            return
        
        # 获取历史数据
        history_data = self.data_fetcher(self.history_limit)
        if not history_data:
            self.completer.setModel(None)
            return
        
        # 过滤数据
        current_text = self.text().strip()
        if current_text:
            filtered_data = [item for item in history_data 
                           if current_text.lower() in item.lower()]
        else:
            filtered_data = history_data
        
        # 更新模型
        if filtered_data:
            model = QStringListModel(filtered_data)
            self.completer.setModel(model)
        else:
            self.completer.setModel(None)


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
        
        # 启用拖拽功能
        self.setAcceptDrops(True)
        
        self.init_ui()
        
        # 如果是编辑模式，预填数据
        if self.is_edit_mode:
            self.populate_edit_data()
        
        # 保存初始数据状态
        self.save_original_data()
        
        # 连接所有输入控件的信号来检测变化
        self.connect_change_signals()
        
        self.resize(1000, 600)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            file_paths = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    file_paths.append(file_path)
            
            if file_paths:
                if self.is_edit_mode:
                    # 编辑模式：弹窗询问是否导入附件
                    reply = QMessageBox.question(
                        self,
                        '确认导入',
                        f'是否将{len(file_paths)}个文件导入附件？',
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        visit_record_id = self.edit_record.get('visit_record_id') if self.edit_record else None
                        if visit_record_id:
                            success_count = 0
                            for file_path in file_paths:
                                if self.data_storage.add_attachment_to_visit(self.user_name, visit_record_id, file_path):
                                    success_count += 1
                            
                            if success_count > 0:
                                self.load_edit_mode_attachments()  # 重新加载列表
                            else:
                                QMessageBox.warning(self, "失败", "附件添加失败")
                        else:
                            QMessageBox.warning(self, "错误", "无法获取就诊记录ID")
                else:
                    # 新增模式：直接将路径写入附件展示区
                    for file_path in file_paths:
                        item = QListWidgetItem()
                        checkbox = QCheckBox()
                        checkbox.setChecked(False)
                        self.attachment_list.addItem(item)
                        self.attachment_list.setItemWidget(item, checkbox)
                        item.setData(Qt.ItemDataRole.UserRole, file_path)
                        checkbox.setText(file_path)
                    self._update_placeholder()
                    # 标记有未保存的变化
                    self.on_data_changed()
            
            event.acceptProposedAction()
        else:
            event.ignore()

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
        self.hospital_edit = AutoCompleteLineEdit("医院名称输入框", history_limit=5)
        # 设置数据获取函数，使用 lambda 传递 user_name 参数
        self.hospital_edit.set_data_fetcher(
            lambda limit: self.data_storage.get_history_hospitals(self.user_name, limit)
        )
        
        hospital_hbox = QHBoxLayout()
        hospital_hbox.setSpacing(6)
        hospital_hbox.addWidget(hospital_label)
        hospital_hbox.addWidget(self.hospital_edit)
        hospital_hbox.addStretch()

        department_label = QLabel('科室名称')
        self.department_edit = AutoCompleteLineEdit("科室名称输入框", history_limit=5)
        # 设置数据获取函数，根据医院名称筛选科室
        self.department_edit.set_data_fetcher(
            lambda limit: self.data_storage.get_history_departments_by_hospital(
                self.user_name, 
                self.hospital_edit.text().strip(), 
                limit
            )
        )
        
        department_hbox = QHBoxLayout()
        department_hbox.setSpacing(6)
        department_hbox.addWidget(department_label)
        department_hbox.addWidget(self.department_edit)
        department_hbox.addStretch()

        doctor_label = QLabel('医生名称')
        self.doctor_edit = AutoCompleteLineEdit("医生名称输入框", history_limit=5)
        # 设置数据获取函数，根据医院名称筛选医生
        self.doctor_edit.set_data_fetcher(
            lambda limit: self.data_storage.get_history_doctors(
                self.user_name, 
                self.hospital_edit.text().strip(), 
                limit
            )
        )
        
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
        attach_btn_h = QHBoxLayout()
        
        if self.is_edit_mode:
            # 编辑模式下直接使用3个附件管理按钮
            self.add_attachment_btn = QPushButton('添加附件')
            self.remove_attachment_btn = QPushButton('删除选中')
            self.view_attachment_btn = QPushButton('查看附件')
            
            self.add_attachment_btn.clicked.connect(self.add_edit_attachment)
            self.remove_attachment_btn.clicked.connect(self.remove_edit_attachment)
            self.view_attachment_btn.clicked.connect(self.view_edit_attachment)
            
            attach_btn_h.addWidget(self.add_attachment_btn)
            attach_btn_h.addWidget(self.remove_attachment_btn)
            attach_btn_h.addWidget(self.view_attachment_btn)
            attach_btn_h.addStretch()
            
            # 根据模式设置按钮文本
            self.upload_btn = QPushButton('保存修改')
        else:
            # 新增模式下使用原有的附件按钮
            self.add_attachment_btn = QPushButton('添加附件按钮')
            self.remove_attachment_btn = QPushButton('移除附件按钮')
            self.remove_all_attachment_btn = QPushButton('移除所有附件按钮')
            
            self.add_attachment_btn.clicked.connect(self.add_attachment)
            self.remove_attachment_btn.clicked.connect(self.remove_attachment)
            self.remove_all_attachment_btn.clicked.connect(self.remove_all_attachment)
            
            attach_btn_h.addWidget(self.add_attachment_btn)
            attach_btn_h.addWidget(self.remove_attachment_btn)
            attach_btn_h.addWidget(self.remove_all_attachment_btn)
            attach_btn_h.addStretch()
            
            # 根据模式设置按钮文本
            self.upload_btn = QPushButton('上传本次记录按钮')
        
        self.upload_btn.clicked.connect(self.upload_visit_record)

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
        
        if not self.is_edit_mode:
            # 只有在新增模式下才连接信号和更新占位符
            self.attachment_list.itemChanged.connect(self._update_placeholder)
            self._update_placeholder()
        else:
            # 编辑模式下支持选择但禁用编辑
            self.attachment_list.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
            self.attachment_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
            # 连接双击事件
            self.attachment_list.doubleClicked.connect(self.on_attachment_double_clicked)

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
        bottom_btn_h.addWidget(self.upload_btn)
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
        
        # 连接医院名称输入框的文本改变信号，以便更新科室名称的候选列表
        self.hospital_edit.textChanged.connect(self._on_hospital_changed)

    def _on_hospital_changed(self):
        """医院名称改变时的处理"""
        # 触发科室名称输入框的候选列表更新
        self.department_edit._update_completer()
        
        # 触发医生名称输入框的候选列表更新
        self.doctor_edit._update_completer()
        
        # 如果医院名称为空，清空科室名称输入框
        if not self.hospital_edit.text().strip():
            self.department_edit.clear()

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
    
    def add_edit_attachment(self):
        """编辑模式下添加附件"""
        if not self.is_edit_mode or not self.edit_record:
            return
            
        visit_record_id = self.edit_record.get('visit_record_id')
        if not visit_record_id:
            QMessageBox.warning(self, "错误", "无法获取就诊记录ID")
            return
        
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择附件')
        
        if file_paths:
            success_count = 0
            for file_path in file_paths:
                if self.data_storage.add_attachment_to_visit(self.user_name, visit_record_id, file_path):
                    success_count += 1
            
            if success_count > 0:
                self.load_edit_mode_attachments()  # 重新加载列表
            else:
                QMessageBox.warning(self, "失败", "附件添加失败")
    
    def remove_edit_attachment(self):
        """编辑模式下删除选中的附件"""
        if not self.is_edit_mode or not self.edit_record:
            return
        
        selected_items = self.attachment_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的附件")
            return
        
        selected_attachments = []
        for item in selected_items:
            attachment_data = item.data(Qt.ItemDataRole.UserRole)
            if attachment_data:  # 确保不是占位符项目
                selected_attachments.append(attachment_data)
        
        if not selected_attachments:
            QMessageBox.information(self, "提示", "请选择有效的附件")
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
                self.load_edit_mode_attachments()  # 重新加载列表
            else:
                QMessageBox.warning(self, "失败", "附件删除失败")
    
    def view_edit_attachment(self):
        """编辑模式下查看选中的附件"""
        if not self.is_edit_mode or not self.edit_record:
            return
        
        selected_items = self.attachment_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要查看的附件")
            return
        
        # 查看第一个选中的附件
        item = selected_items[0]
        attachment_data = item.data(Qt.ItemDataRole.UserRole)
        if not attachment_data:
            QMessageBox.information(self, "提示", "请选择有效的附件")
            return
        
        self.open_file(attachment_data)
    
    def on_attachment_double_clicked(self, index):
        """双击附件时的处理"""
        if not self.is_edit_mode:
            return
            
        item = self.attachment_list.itemFromIndex(index)
        if not item:
            return
        
        attachment_data = item.data(Qt.ItemDataRole.UserRole)
        if not attachment_data:
            return
        
        self.open_file(attachment_data)
    
    def replace_edit_attachment(self, attachment_data: dict):
        """替换现有附件"""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(self, '选择新的附件文件')
        
        if file_paths:
            # 只取第一个文件来替换
            new_file_path = file_paths[0]
            attachment_id = attachment_data['attachment_id']
            
            # 更新附件记录的路径
            if self.data_storage.update_attachment_path(self.user_name, attachment_id, new_file_path):
                self.load_edit_mode_attachments()  # 重新加载列表
            else:
                QMessageBox.warning(self, "失败", "更新附件路径失败")
    
    def open_file(self, attachment_data: dict):
        """打开文件"""
        file_path = attachment_data['file_path']
        
        if not os.path.exists(file_path):
            # 文件不存在时，弹出包含三个选项的对话框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("文件不存在")
            msg_box.setText(f"文件不存在：{file_path}")
            msg_box.setInformativeText("请选择要执行的操作：")
            
            # 添加自定义按钮
            delete_btn = msg_box.addButton("删除记录", QMessageBox.ButtonRole.ActionRole)
            add_btn = msg_box.addButton("添加附件", QMessageBox.ButtonRole.ActionRole)  
            ignore_btn = msg_box.addButton("忽略", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.setDefaultButton(ignore_btn)
            msg_box.exec()
            
            # 根据用户选择执行相应操作
            if msg_box.clickedButton() == delete_btn:
                # 删除附件记录
                if self.data_storage.delete_attachment(self.user_name, attachment_data['attachment_id']):
                    self.load_edit_mode_attachments()  # 重新加载列表
                else:
                    QMessageBox.warning(self, "失败", "删除附件记录失败")
            elif msg_box.clickedButton() == add_btn:
                # 替换现有附件
                self.replace_edit_attachment(attachment_data)
            # 如果是忽略，则什么都不做
            return
        
        try:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                os.startfile(file_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件：{str(e)}")
    
    def load_edit_mode_attachments(self):
        """加载编辑模式下的附件信息"""
        if not self.is_edit_mode or not self.edit_record:
            return
            
        visit_record_id = self.edit_record.get('visit_record_id')
        if not visit_record_id:
            return
        
        # 清空现有列表
        self.attachment_list.clear()
        
        # 从数据库获取附件信息
        attachments = self.data_storage.get_visit_attachments(self.user_name, visit_record_id)
        
        if not attachments:
            # 显示无附件提示
            placeholder_item = QListWidgetItem("当前就诊记录暂无附件")
            placeholder_item.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder_item.setForeground(Qt.GlobalColor.gray)
            self.attachment_list.addItem(placeholder_item)
        else:
            # 显示附件信息（可选择）
            for attachment in attachments:
                item = QListWidgetItem(f"📎 {attachment['file_name']}")
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setData(Qt.ItemDataRole.UserRole, attachment)
                self.attachment_list.addItem(item)

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
        
        # 只在新增模式下连接附件列表的信号
        if not self.is_edit_mode:
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
        if self.is_edit_mode and self.edit_record:
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
        # 获取所有附件文件路径（仅在新增模式下从attachment_list收集）
        attachment_paths = []
        if not self.is_edit_mode:
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
        }
        
        # 只在新增模式下添加附件路径
        if not self.is_edit_mode:
            visit_data['attachment_paths'] = attachment_paths
        
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
        
        # 加载附件信息
        self.load_edit_mode_attachments() 