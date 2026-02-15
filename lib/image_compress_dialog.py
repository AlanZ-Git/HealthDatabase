"""
图片压缩PDF对话框
使用拖拽方式选择文件夹，将文件夹内的图片压缩后合并为PDF
"""
import os
import re
import shutil
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PIL import Image


class CompressWorker(QThread):
    """后台压缩工作线程"""

    # 信号定义
    progress_update = pyqtSignal(str)  # 进度更新（文本）
    progress_percent = pyqtSignal(int)  # 进度百分比
    finished = pyqtSignal(dict)  # 完成信号（传递结果）

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        # 固定参数
        self.image_quality = 50
        self.max_dimension = 2560
        self.pdf_quality = 50

    def run(self):
        """执行压缩流程"""
        result = self.compress_folder_to_pdf(
            self.folder_path,
            self.image_quality,
            self.max_dimension,
            self.pdf_quality
        )
        self.finished.emit(result)

    @staticmethod
    def natural_sort_key(text: str) -> list:
        """自然排序键函数,支持page_1, page_2, page_10等排序"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]

    @staticmethod
    def compress_image(img_path: Path, output_path: Path, quality: int = 50, max_dimension: int = 2560) -> bool:
        """压缩单张图片"""
        try:
            with Image.open(img_path) as img:
                width, height = img.size

                # 检查是否需要调整分辨率
                if width > max_dimension or height > max_dimension:
                    # 计算缩放比例,保持宽高比
                    if width > height:
                        new_width = max_dimension
                        new_height = int(height * (max_dimension / width))
                    else:
                        new_height = max_dimension
                        new_width = int(width * (max_dimension / height))
                    new_size = (new_width, new_height)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # 转换为RGB模式(JPEG需要)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 保存为JPEG格式
                img.save(output_path, 'JPEG', quality=quality, optimize=True)

            return True
        except Exception:
            return False

    def merge_images_to_pdf(self, images_dir: Path, output_pdf: Path, quality: int = 50) -> dict:
        """将指定目录下的图片合并为PDF"""
        # 查找所有图片文件
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.bmp', '*.gif', '*.tiff', '*.tif', '*.webp']:
            image_files.extend(images_dir.glob(ext))

        # 去重
        image_files = list(dict.fromkeys(image_files))

        if not image_files:
            return {
                'success': False,
                'error': '目录中没有找到图片文件',
                'total': 0,
                'merged': 0,
                'failed': []
            }

        # 按文件名自然排序
        image_files.sort(key=lambda x: self.natural_sort_key(x.name))

        # 打开所有图片
        images = []
        failed_files = []

        for i, img_file in enumerate(image_files):
            self.progress_update.emit(f"正在加载: {img_file.name}")
            try:
                img = Image.open(img_file)

                # 转换为RGB模式(PDF需要)
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                images.append(img)
                # 更新进度
                percent = int((i + 1) / len(image_files) * 50)
                self.progress_percent.emit(percent)

            except Exception as e:
                failed_files.append(str(img_file))

        # 检查是否有可用的图片
        if not images:
            return {
                'success': False,
                'error': '没有成功加载任何图片',
                'total': len(image_files),
                'merged': 0,
                'failed': failed_files
            }

        # 保存为PDF
        self.progress_update.emit("正在保存PDF...")
        try:
            images[0].save(
                output_pdf,
                save_all=True,
                append_images=images[1:],
                quality=quality,
                optimize=False
            )
            self.progress_percent.emit(100)

        except Exception as e:
            return {
                'success': False,
                'error': f'保存PDF失败: {e}',
                'total': len(image_files),
                'merged': len(images),
                'failed': failed_files
            }

        # 关闭所有图片
        for img in images:
            img.close()

        return {
            'success': True,
            'total': len(image_files),
            'merged': len(images),
            'failed': failed_files,
            'output_path': str(output_pdf),
            'output_size': output_pdf.stat().st_size if output_pdf.exists() else 0
        }

    def compress_folder_to_pdf(self, folder_path: str, image_quality: int = 50,
                               max_dimension: int = 2560, pdf_quality: int = 50) -> dict:
        """将文件夹内的图片压缩后合并为PDF"""
        folder = Path(folder_path)

        # 验证输入文件夹
        if not folder.exists():
            return {'success': False, 'error': '文件夹不存在'}

        if not folder.is_dir():
            return {'success': False, 'error': '路径不是文件夹'}

        # 记录文件夹名称
        folder_name = folder.name

        # 创建临时文件夹
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        temp_folder = folder.parent / f"TEMP{timestamp}"

        try:
            temp_folder.mkdir(parents=True, exist_ok=True)
            self.progress_update.emit(f"创建临时文件夹...")
        except Exception as e:
            return {'success': False, 'error': f'创建临时文件夹失败: {e}'}

        # 支持的图片格式
        supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}

        # 查找所有图片文件
        image_files = []
        for ext in supported_formats:
            image_files.extend(folder.glob(f'*{ext}'))

        # 去重
        image_files = list(dict.fromkeys(image_files))

        if not image_files:
            shutil.rmtree(temp_folder)
            return {'success': False, 'error': '未找到支持的图片文件'}

        self.progress_update.emit(f"找到 {len(image_files)} 张图片")

        # 压缩所有图片到临时文件夹
        success_count = 0
        error_count = 0

        for i, img_path in enumerate(image_files):
            output_path = temp_folder / f"{img_path.stem}.jpg"
            self.progress_update.emit(f"压缩中: {img_path.name} ({i+1}/{len(image_files)})")

            if self.compress_image(img_path, output_path, image_quality, max_dimension):
                success_count += 1
            else:
                error_count += 1

            # 更新进度（前50%用于压缩）
            percent = int((i + 1) / len(image_files) * 50)
            self.progress_percent.emit(percent)

        # 合并为PDF
        output_pdf = folder.parent / f"{folder_name}.pdf"
        result = self.merge_images_to_pdf(temp_folder, output_pdf, pdf_quality)

        # 删除临时文件夹
        try:
            shutil.rmtree(temp_folder)
        except Exception:
            pass  # 忽略删除失败

        return result


class ImageCompressDialog(QDialog):
    """图片压缩PDF对话框 - 支持拖拽文件夹"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('图片压缩PDF')
        self.setFixedSize(500, 350)
        self.setModal(True)

        # 工作线程
        self.worker = None

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题和图标
        title_label = QLabel('图片压缩PDF')
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #104d8f;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 拖拽区域提示
        drag_hint_label = QLabel("""
            <div style='text-align: center;'>
                <p style='font-size: 16px;'><b>📁 拖拽文件夹</b></p>
                <p style='font-size: 14px; color: #666;'>将包含图片的文件夹拖拽到此窗口</p>
                <p style='font-size: 12px; color: #999;'>支持格式: JPG, PNG, BMP, TIFF, GIF, WEBP</p>
            </div>
        """)
        drag_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_hint_label.setWordWrap(True)
        layout.addWidget(drag_hint_label)

        # 分隔线
        separator = QLabel('<hr style="border: 1px solid #ddd;">')
        layout.addWidget(separator)

        # 状态标签
        self.status_label = QLabel('状态: 等待拖拽文件夹...')
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #666;
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #104d8f;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        self.setLayout(layout)

        # 设置样式表
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
        """)

        # 设置接受拖拽（不使用DragDropMixin，因为我们自定义处理）
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件 - 只接受文件夹"""
        if event.mimeData().hasUrls():
            # 检查是否为文件夹
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    event.acceptProposedAction()
                    self.status_label.setText('状态: 释放鼠标以开始处理...')
                    self.status_label.setStyleSheet("""
                        QLabel {
                            font-size: 13px;
                            color: #104d8f;
                            padding: 10px;
                            background-color: #e6f2ff;
                            border-radius: 5px;
                            border: 2px solid #104d8f;
                        }
                    """)
                    return

        # 如果不是文件夹，忽略
        event.ignore()
        self.status_label.setText('状态: 请拖拽文件夹（不是文件）')
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #d9534f;
                padding: 10px;
                background-color: #f9f2f2;
                border-radius: 5px;
            }
        """)

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self.status_label.setText('状态: 等待拖拽文件夹...')
        self.status_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #666;
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件 - 处理文件夹"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                path = url.toLocalFile()
                # 检查是否为文件夹
                if os.path.isdir(path):
                    event.acceptProposedAction()
                    # 开始压缩处理
                    self.start_compression(path)
                    return

        # 如果不是文件夹，显示错误
        event.ignore()
        QMessageBox.warning(self, '错误', '请拖拽文件夹，而不是文件')

    def start_compression(self, folder_path: str):
        """开始压缩处理"""
        # 更新UI状态
        self.status_label.setText(f'状态: 正在处理...')
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # 禁用拖拽（防止重复拖拽）
        self.setAcceptDrops(False)

        # 创建工作线程
        self.worker = CompressWorker(folder_path)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.progress_percent.connect(self.on_progress_percent)
        self.worker.finished.connect(self.on_compression_finished)
        self.worker.start()

    def on_progress_update(self, message: str):
        """更新进度文本"""
        self.status_label.setText(f'状态: {message}')

    def on_progress_percent(self, percent: int):
        """更新进度百分比"""
        self.progress_bar.setValue(percent)

    def on_compression_finished(self, result: dict):
        """压缩完成处理"""
        # 恢复拖拽功能
        self.setAcceptDrops(True)

        if result['success']:
            # 显示成功消息
            file_size_kb = result.get('output_size', 0) / 1024
            file_size_mb = file_size_kb / 1024

            size_text = f"{file_size_mb:.2f} MB" if file_size_mb >= 1 else f"{file_size_kb:.2f} KB"

            message = f"""
✅ 压缩完成！

成功处理: {result['merged']} 张图片
失败: {len(result.get('failed', []))} 张

输出文件: {result.get('output_path', '未知')}
文件大小: {size_text}
            """.strip()

            QMessageBox.information(self, '压缩完成', message)

            # 重置UI
            self.status_label.setText('状态: 等待拖拽文件夹...')
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #666;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                }
            """)
            self.progress_bar.setVisible(False)

        else:
            # 显示错误消息
            error_msg = result.get('error', '未知错误')
            QMessageBox.critical(self, '压缩失败', f'❌ 压缩失败\n\n{error_msg}')

            # 重置UI
            self.status_label.setText('状态: 等待拖拽文件夹...')
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 13px;
                    color: #666;
                    padding: 10px;
                    background-color: #f5f5f5;
                    border-radius: 5px;
                }
            """)
            self.progress_bar.setVisible(False)

        # 清理工作线程
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
