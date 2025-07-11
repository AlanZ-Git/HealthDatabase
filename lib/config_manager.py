import configparser
import os
from typing import Tuple, Dict, Any, Optional
from PyQt6.QtWidgets import QApplication, QWidget


class ConfigManager:
    """统一配置管理器，负责处理settings.ini和history.ini的所有配置操作"""
    
    def __init__(self):
        self.settings_file = 'settings.ini'
        self.history_file = 'history.ini'
        
        # 确保配置文件存在
        self._ensure_config_files()
    
    def _ensure_config_files(self):
        """确保配置文件存在"""
        if not os.path.exists(self.settings_file):
            self._create_default_settings()
    
    def _create_default_settings(self):
        """创建默认settings.ini文件"""
        config = configparser.ConfigParser()
        
        # 默认显示设置
        config['Display'] = {
            'font_scale': '1.2'
        }
        
        # 默认固定列宽
        config['FixedColumnWidths'] = {
            'column_0': '50',
            'column_1': '55', 
            'column_2': '93',
            'column_5': '61',
            'column_6': '102',
            'column_11': '80'
        }
        
        # 默认比例列宽
        config['ProportionalColumnWidths'] = {
            'column_3': '0.20',
            'column_4': '0.15', 
            'column_7': '0.25',
            'column_8': '0.20',
            'column_9': '0.12',
            'column_10': '0.08'
        }
        
        # 默认分页设置
        config['Pagination'] = {
            'records_per_page': '15'
        }
        
        # 默认窗口设置
        config['Window'] = {
            'width': '1200',
            'height': '800'
        }
        
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def _read_config(self, filename: str) -> configparser.ConfigParser:
        """读取配置文件"""
        config = configparser.ConfigParser()
        if os.path.exists(filename):
            config.read(filename, encoding='utf-8')
        return config
    
    def _write_config(self, filename: str, config: configparser.ConfigParser):
        """写入配置文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            config.write(f)
    
    def _get_config_value(self, section: str, key: str, default: Any = None, use_history_first: bool = True) -> Any:
        """
        获取配置值，优先从history.ini读取，然后从settings.ini读取
        
        Args:
            section: 配置节名
            key: 配置键名
            default: 默认值
            use_history_first: 是否优先使用历史配置
        """
        if use_history_first:
            # 首先尝试从history.ini读取
            history_config = self._read_config(self.history_file)
            if history_config.has_section(section) and history_config.has_option(section, key):
                return history_config.get(section, key)
        
        # 然后从settings.ini读取
        settings_config = self._read_config(self.settings_file)
        if settings_config.has_section(section) and settings_config.has_option(section, key):
            return settings_config.get(section, key)
        
        return default
    
    def _set_config_value(self, section: str, key: str, value: str, save_to_history: bool = True):
        """
        设置配置值
        
        Args:
            section: 配置节名
            key: 配置键名  
            value: 配置值
            save_to_history: 是否保存到history.ini（用户偏好）
        """
        filename = self.history_file if save_to_history else self.settings_file
        config = self._read_config(filename)
        
        if not config.has_section(section):
            config.add_section(section)
        
        config.set(section, key, str(value))
        self._write_config(filename, config)
    
    # ==================== 窗口大小和位置管理 ====================
    
    def get_window_size(self) -> Tuple[int, int]:
        """获取窗口大小，优先用户设置，回退到默认设置"""
        try:
            width = int(self._get_config_value('Window', 'width', '1200'))
            height = int(self._get_config_value('Window', 'height', '800'))
            return width, height
        except (ValueError, TypeError):
            return 1200, 800
    
    def save_window_size(self, width: int, height: int):
        """保存窗口大小到用户历史"""
        self._set_config_value('Window', 'width', str(width))
        self._set_config_value('Window', 'height', str(height))
    
    def get_window_position(self) -> Optional[Tuple[int, int]]:
        """获取窗口位置，优先用户设置"""
        try:
            x = self._get_config_value('Window', 'x')
            y = self._get_config_value('Window', 'y')
            if x is not None and y is not None:
                return int(x), int(y)
        except (ValueError, TypeError):
            pass
        return None
    
    def save_window_position(self, x: int, y: int):
        """保存窗口位置到用户历史"""
        self._set_config_value('Window', 'x', str(x))
        self._set_config_value('Window', 'y', str(y))
    
    def get_window_maximized(self) -> bool:
        """获取窗口最大化状态"""
        try:
            maximized = self._get_config_value('Window', 'maximized', 'false')
            return maximized.lower() == 'true'
        except (ValueError, TypeError):
            return False
    
    def save_window_maximized(self, maximized: bool):
        """保存窗口最大化状态到用户历史"""
        self._set_config_value('Window', 'maximized', str(maximized).lower())
    
    def center_window_on_screen(self, widget: QWidget):
        """窗口居中显示逻辑"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = widget.geometry()
        
        x = (screen.width() - window_geometry.width()) // 2
        y = (screen.height() - window_geometry.height()) // 2
        
        widget.move(x, y)
    
    def apply_window_settings(self, widget: QWidget):
        """应用窗口设置（大小和位置）"""
        # 先检查是否应该最大化
        if self.get_window_maximized():
            # 先设置正常大小，然后最大化
            width, height = self.get_window_size()
            widget.resize(width, height)
            widget.showMaximized()
        else:
            # 设置窗口大小
            width, height = self.get_window_size()
            widget.resize(width, height)
            
            # 设置窗口位置
            position = self.get_window_position()
            if position:
                widget.move(position[0], position[1])
            else:
                self.center_window_on_screen(widget)
    
    def save_window_settings(self, widget: QWidget):
        """保存窗口设置（大小、位置和最大化状态）"""
        # 保存最大化状态
        is_maximized = widget.isMaximized()
        self.save_window_maximized(is_maximized)
        
        if not is_maximized:
            # 只有在非最大化状态下才保存窗口大小和位置
            self.save_window_size(widget.width(), widget.height())
            self.save_window_position(widget.x(), widget.y())
        # 如果是最大化状态，则不更新窗口大小和位置，保持之前的设置
    
    # ==================== 字体缩放管理 ====================
    
    def get_font_scale(self) -> float:
        """获取字体缩放比例"""
        try:
            return float(self._get_config_value('Display', 'font_scale', '1.2', use_history_first=False))
        except (ValueError, TypeError):
            return 1.2
    
    def save_font_scale(self, scale: float):
        """保存字体缩放比例到默认设置"""
        self._set_config_value('Display', 'font_scale', str(scale), save_to_history=False)
    
    # ==================== 用户选择管理 ====================
    
    def get_last_user(self) -> Optional[str]:
        """获取最后选择的用户"""
        return self._get_config_value('History', 'last_user')
    
    def save_last_user(self, user_name: str):
        """保存最后选择的用户"""
        self._set_config_value('History', 'last_user', user_name)
    
    # ==================== 列宽管理 ====================
    
    def get_column_widths(self) -> Tuple[Dict[int, int], Dict[int, float]]:
        """
        获取列宽配置
        
        Returns:
            (固定列宽字典, 比例列宽字典)
        """
        # 固定列
        fixed_columns = [0, 1, 2, 5, 6, 11]
        proportional_columns = [3, 4, 7, 8, 9, 10]
        
        # 获取固定列宽（优先从history.ini读取用户设置）
        fixed_widths = {}
        for col in fixed_columns:
            key = f'column_{col}'
            try:
                width = int(self._get_config_value('FixedColumnWidths', key, '50'))
                fixed_widths[col] = width
            except (ValueError, TypeError):
                fixed_widths[col] = 50
        
        # 获取比例列宽（优先从history.ini读取用户设置）
        proportional_widths = {}
        for col in proportional_columns:
            key = f'column_{col}'
            try:
                proportion = float(self._get_config_value('ProportionalColumnWidths', key, '0.1'))
                proportional_widths[col] = proportion
            except (ValueError, TypeError):
                proportional_widths[col] = 0.1
        
        # 归一化比例值
        total_proportion = sum(proportional_widths.values())
        if total_proportion > 0:
            proportional_widths = {
                col: proportion / total_proportion 
                for col, proportion in proportional_widths.items()
            }
        
        return fixed_widths, proportional_widths
    
    def save_column_widths(self, fixed_widths: Dict[int, int], proportional_widths: Dict[int, float]):
        """保存列宽配置到用户历史"""
        # 保存固定列宽
        for col, width in fixed_widths.items():
            self._set_config_value('FixedColumnWidths', f'column_{col}', str(width))
        
        # 保存比例列宽
        for col, proportion in proportional_widths.items():
            self._set_config_value('ProportionalColumnWidths', f'column_{col}', str(proportion))
    
    def reset_column_widths(self):
        """重置列宽为默认设置"""
        # 删除history.ini中的列宽设置
        config = self._read_config(self.history_file)
        
        if config.has_section('FixedColumnWidths'):
            config.remove_section('FixedColumnWidths')
        if config.has_section('ProportionalColumnWidths'):
            config.remove_section('ProportionalColumnWidths')
        
        self._write_config(self.history_file, config)
    
    # ==================== 分页设置管理 ====================
    
    def get_records_per_page(self) -> int:
        """获取每页记录数"""
        try:
            return int(self._get_config_value('Pagination', 'records_per_page', '15'))
        except (ValueError, TypeError):
            return 15
    
    def save_records_per_page(self, records_per_page: int):
        """保存每页记录数到用户历史"""
        self._set_config_value('Pagination', 'records_per_page', str(records_per_page)) 