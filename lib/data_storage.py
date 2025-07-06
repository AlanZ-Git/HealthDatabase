import sqlite3
import os
import glob
from tkinter import NO
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class DataStorage:
    """数据库存储管理类，负责所有数据库操作"""
    
    def __init__(self, data_dir: str = 'data'):
        """
        初始化数据存储管理器
        
        Args:
            data_dir: 数据文件目录
        """
        self.data_dir = data_dir
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _get_db_path(self, user_name: str) -> str:
        """获取用户数据库文件路径"""
        return os.path.join(self.data_dir, f'{user_name}.sqlite')
    
    def get_all_users(self) -> List[str]:
        """
        获取所有用户列表
        
        Returns:
            用户名列表
        """
        if not os.path.exists(self.data_dir):
            return []
        
        sqlite_files = glob.glob(os.path.join(self.data_dir, '*.sqlite'))
        users = []
        for file_path in sqlite_files:
            user_name = os.path.splitext(os.path.basename(file_path))[0]
            users.append(user_name)
        
        return users
    
    def create_user(self, user_name: str) -> bool:
        """
        创建新用户
        
        Args:
            user_name: 用户名
            
        Returns:
            是否创建成功
        """
        try:
            # 检查用户是否已存在
            if user_name in self.get_all_users():
                return False
            
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建就诊记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visit_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hospital TEXT,
                    department TEXT,
                    doctor TEXT,
                    organ_system TEXT,
                    reason TEXT,
                    diagnosis TEXT,
                    medication TEXT,
                    remark TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建附件记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attachment_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    visit_record_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    FOREIGN KEY (visit_record_id) REFERENCES visit_records(id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"创建用户失败: {e}")
            return False
    
    def delete_user(self, user_name: str) -> bool:
        """
        删除用户
        
        Args:
            user_name: 用户名
            
        Returns:
            是否删除成功
        """
        try:
            db_path = self._get_db_path(user_name)
            if os.path.exists(db_path):
                os.remove(db_path)
                return True
            return False
        except Exception as e:
            print(f"删除用户失败: {e}")
            return False
    

    def get_user_history(self, user_name: str, field: str, limit: int = 5) -> List[str]:
        """
        获取用户历史输入记录（用于自动补全）
        
        Args:
            user_name: 用户名
            field: 字段名（hospital, department, doctor）
            limit: 返回记录数量限制
            
        Returns:
            历史记录列表
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 构建查询语句
            query = f'''
                SELECT DISTINCT {field}
                FROM visit_records 
                WHERE {field} IS NOT NULL AND {field} != ''
                ORDER BY updated_at DESC
                LIMIT {limit}
            '''
            
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except Exception as e:
            print(f"获取用户历史记录失败: {e}")
            return []
    
    def get_doctors_by_hospital(self, user_name: str, hospital: str, limit: int = 5) -> List[str]:
        """
        根据医院名称获取医生列表
        
        Args:
            user_name: 用户名
            hospital: 医院名称
            limit: 返回记录数量限制
            
        Returns:
            医生名称列表
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT doctor
                FROM visit_records 
                WHERE hospital = ? AND doctor IS NOT NULL AND doctor != ''
                ORDER BY updated_at DESC
                LIMIT ?
            ''', (hospital, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in results]
            
        except Exception as e:
            print(f"获取医生列表失败: {e}")
            return []
