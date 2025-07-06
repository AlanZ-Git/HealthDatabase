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
            
            # 创建就诊记录表  TODO: 需要检查是否正确
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS visit_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    hospital TEXT,
                    department TEXT,
                    doctor TEXT,
                    system TEXT,
                    reason TEXT,
                    diagnosis TEXT,
                    medication TEXT,
                    remark TEXT,
                    attachments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def add_visit_record(self, user_name: str, record_data: Dict) -> bool:
        """
        添加就诊记录
        
        Args:
            user_name: 用户名
            record_data: 记录数据字典
            
        Returns:
            是否添加成功
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 处理附件路径列表
            attachments = record_data.get('attachments', [])
            attachments_str = ';'.join(attachments) if attachments else ''
            
            cursor.execute('''
                INSERT INTO visit_records 
                (date, hospital, department, doctor, system, reason, diagnosis, medication, remark, attachments)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record_data.get('date', ''),
                record_data.get('hospital', ''),
                record_data.get('department', ''),
                record_data.get('doctor', ''),
                record_data.get('system', ''),
                record_data.get('reason', ''),
                record_data.get('diagnosis', ''),
                record_data.get('medication', ''),
                record_data.get('remark', ''),
                attachments_str
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加就诊记录失败: {e}")
            return False
    
    def get_visit_records(self, user_name: str, limit: Optional[int] = None) -> List[Dict]:
        """
        获取就诊记录列表
        
        Args:
            user_name: 用户名
            limit: 限制返回记录数量
            
        Returns:
            就诊记录列表
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, date, hospital, department, doctor, system, reason, 
                       diagnosis, medication, remark, attachments, created_at, updated_at
                FROM visit_records 
                ORDER BY created_at DESC
            '''
            
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query)
            records = cursor.fetchall()
            
            result = []
            for record in records:
                attachments = record[10].split(';') if record[10] else []
                result.append({
                    'id': record[0],
                    'date': record[1],
                    'hospital': record[2],
                    'department': record[3],
                    'doctor': record[4],
                    'system': record[5],
                    'reason': record[6],
                    'diagnosis': record[7],
                    'medication': record[8],
                    'remark': record[9],
                    'attachments': attachments,
                    'created_at': record[11],
                    'updated_at': record[12]
                })
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"获取就诊记录失败: {e}")
            return []
    
    def get_visit_record(self, user_name: str, record_id: int) -> Optional[Dict]:
        """
        获取单条就诊记录
        
        Args:
            user_name: 用户名
            record_id: 记录ID
            
        Returns:
            就诊记录字典，如果不存在返回None
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, date, hospital, department, doctor, system, reason, 
                       diagnosis, medication, remark, attachments, created_at, updated_at
                FROM visit_records 
                WHERE id = ?
            ''', (record_id,))
            
            record = cursor.fetchone()
            conn.close()
            
            if record:
                attachments = record[10].split(';') if record[10] else []
                return {
                    'id': record[0],
                    'date': record[1],
                    'hospital': record[2],
                    'department': record[3],
                    'doctor': record[4],
                    'system': record[5],
                    'reason': record[6],
                    'diagnosis': record[7],
                    'medication': record[8],
                    'remark': record[9],
                    'attachments': attachments,
                    'created_at': record[11],
                    'updated_at': record[12]
                }
            
            return None
            
        except Exception as e:
            print(f"获取就诊记录失败: {e}")
            return None
    
    def update_visit_record(self, user_name: str, record_id: int, record_data: Dict) -> bool:
        """
        更新就诊记录
        
        Args:
            user_name: 用户名
            record_id: 记录ID
            record_data: 更新的记录数据
            
        Returns:
            是否更新成功
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 处理附件路径列表
            attachments = record_data.get('attachments', [])
            attachments_str = ';'.join(attachments) if attachments else ''
            
            cursor.execute('''
                UPDATE visit_records 
                SET date = ?, hospital = ?, department = ?, doctor = ?, system = ?, 
                    reason = ?, diagnosis = ?, medication = ?, remark = ?, attachments = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                record_data.get('date', ''),
                record_data.get('hospital', ''),
                record_data.get('department', ''),
                record_data.get('doctor', ''),
                record_data.get('system', ''),
                record_data.get('reason', ''),
                record_data.get('diagnosis', ''),
                record_data.get('medication', ''),
                record_data.get('remark', ''),
                attachments_str,
                record_id
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"更新就诊记录失败: {e}")
            return False
    
    def delete_visit_record(self, user_name: str, record_id: int) -> bool:
        """
        删除就诊记录
        
        Args:
            user_name: 用户名
            record_id: 记录ID
            
        Returns:
            是否删除成功
        """
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM visit_records WHERE id = ?', (record_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"删除就诊记录失败: {e}")
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
    
    def search_records(self, user_name: str, search_term: str, fields: List[str]|None = None) -> List[Dict]:
        """
        搜索就诊记录
        
        Args:
            user_name: 用户名
            search_term: 搜索关键词
            fields: 搜索字段列表，默认为所有文本字段
            
        Returns:
            匹配的记录列表
        """
        if fields is None:
            fields = ['hospital', 'department', 'doctor', 'system', 'reason', 'diagnosis', 'medication', 'remark']
        
        try:
            db_path = self._get_db_path(user_name)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 构建搜索条件
            search_conditions = []
            params = []
            for field in fields:
                search_conditions.append(f"{field} LIKE ?")
                params.append(f"%{search_term}%")
            
            where_clause = " OR ".join(search_conditions)
            
            query = f'''
                SELECT id, date, hospital, department, doctor, system, reason, 
                       diagnosis, medication, remark, attachments, created_at, updated_at
                FROM visit_records 
                WHERE {where_clause}
                ORDER BY created_at DESC
            '''
            
            cursor.execute(query, params)
            records = cursor.fetchall()
            
            result = []
            for record in records:
                attachments = record[10].split(';') if record[10] else []
                result.append({
                    'id': record[0],
                    'date': record[1],
                    'hospital': record[2],
                    'department': record[3],
                    'doctor': record[4],
                    'system': record[5],
                    'reason': record[6],
                    'diagnosis': record[7],
                    'medication': record[8],
                    'remark': record[9],
                    'attachments': attachments,
                    'created_at': record[11],
                    'updated_at': record[12]
                })
            
            conn.close()
            return result
            
        except Exception as e:
            print(f"搜索记录失败: {e}")
            return [] 