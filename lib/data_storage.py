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
                    visit_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    
    def get_history_hospitals(self, user_name: str, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的医院名称
        
        Args:
            user_name: 用户名
            limit: 返回结果数量限制，默认5个
            
        Returns:
            医院名称列表，按从新到旧排序
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询非空的医院名称，按创建时间倒序排列
            cursor.execute('''
                SELECT DISTINCT hospital 
                FROM visit_records 
                WHERE hospital IS NOT NULL AND hospital != ''
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            hospitals = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return hospitals
            
        except Exception as e:
            print(f"查询历史医院名称失败: {e}")
            return []
    
    def get_history_departments(self, user_name: str, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的科室名称
        
        Args:
            user_name: 用户名
            limit: 返回结果数量限制，默认5个
            
        Returns:
            科室名称列表，按从新到旧排序
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询非空的科室名称，按创建时间倒序排列
            cursor.execute('''
                SELECT DISTINCT department 
                FROM visit_records 
                WHERE department IS NOT NULL AND department != ''
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            
            departments = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return departments
            
        except Exception as e:
            print(f"查询历史科室名称失败: {e}")
            return []
    
    def get_history_doctors(self, user_name: str, hospital: Optional[str] = None, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的医生名称
        
        Args:
            user_name: 用户名
            hospital: 医院名称，如果提供则只查询该医院的医生
            limit: 返回结果数量限制，默认5个
            
        Returns:
            医生名称列表，按从新到旧排序
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            if hospital and hospital.strip():
                # 如果指定了医院，则只查询该医院的医生
                cursor.execute('''
                    SELECT DISTINCT doctor 
                    FROM visit_records 
                    WHERE doctor IS NOT NULL AND doctor != '' 
                    AND hospital = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (hospital, limit))
            else:
                # 查询所有医生
                cursor.execute('''
                    SELECT DISTINCT doctor 
                    FROM visit_records 
                    WHERE doctor IS NOT NULL AND doctor != ''
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            doctors = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            return doctors
            
        except Exception as e:
            print(f"查询历史医生名称失败: {e}")
            return []
    
    def upload_visit_record(self, visit_data: Dict) -> bool:
        """
        上传就诊记录
        
        Args:
            visit_data: 包含就诊信息的字典，格式如下：
            {
                'user_name': '用户名',
                'date': '就诊日期',
                'hospital': '医院名称',
                'department': '科室名称',
                'doctor': '医生名称',
                'organ_system': '器官系统',
                'reason': '就诊原因',
                'diagnosis': '诊断结果',
                'medication': '用药情况',
                'remark': '备注',
                'attachment_paths': ['附件路径列表']
            }
            
        Returns:
            是否上传成功
        """
        try:
            user_name = visit_data.get('user_name')
            if not user_name:
                print("错误：缺少用户名")
                return False
            
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                print(f"错误：用户 {user_name} 的数据库不存在")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 插入就诊记录
            cursor.execute('''
                INSERT INTO visit_records (
                    date, hospital, department, doctor, organ_system,
                    reason, diagnosis, medication, remark
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                visit_data.get('date', None),
                visit_data.get('hospital', None),
                visit_data.get('department', None),
                visit_data.get('doctor', None),
                visit_data.get('organ_system', None),
                visit_data.get('reason', None),
                visit_data.get('diagnosis', None),
                visit_data.get('medication', None),
                visit_data.get('remark', None)
            ))
            
            # 获取刚插入的记录ID
            visit_record_id = cursor.lastrowid
            if visit_record_id is None:
                print("错误：无法获取插入记录的ID")
                conn.rollback()
                conn.close()
                return False
            
            # 处理附件路径
            attachment_paths = visit_data.get('attachment_paths', [])
            if attachment_paths:
                self._process_attachments(cursor, visit_record_id, attachment_paths, user_name)
            
            conn.commit()
            conn.close()
            
            print(f"成功上传就诊记录，记录ID: {visit_record_id}")
            return True
            
        except Exception as e:
            print(f"上传就诊记录失败: {e}")
            return False
    
    def _process_attachments(self, cursor, visit_record_id: int, attachment_paths: List[str], user_name: str):
        """
        处理附件路径
        
        Args:
            cursor: 数据库游标
            visit_record_id: 就诊记录ID
            attachment_paths: 附件路径列表
            user_name: 用户名
        """
        # 确保Appendix目录存在
        appendix_dir = 'Appendix'
        if not os.path.exists(appendix_dir):
            os.makedirs(appendix_dir)
        
        # 确保用户目录存在
        user_dir = os.path.join(appendix_dir, user_name)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        attachment_id = 1
        for attachment_path in attachment_paths:
            if not os.path.exists(attachment_path):
                print(f"警告：附件文件不存在: {attachment_path}")
                continue
            
            try:
                # 获取原文件名和扩展名
                original_name = os.path.basename(attachment_path)
                name, ext = os.path.splitext(original_name)
                
                # 生成新文件名：{visit_record_id}_{attachment_id}_{name}
                new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
                
                # 如果新文件名长度超过100个字符，截断name部分
                if len(new_name) > 100:
                    # 计算可用的name长度：100 - len(visit_record_id) - len(attachment_id) - len(ext) - 2个下划线
                    max_name_length = 100 - len(str(visit_record_id)) - len(str(attachment_id)) - len(ext) - 2
                    if max_name_length > 0:
                        name = name[:max_name_length]
                        new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
                    else:
                        # 如果连基本结构都放不下，使用最简单的命名
                        new_name = f"{visit_record_id}_{attachment_id}{ext}"
                
                # 构建目标路径：{user}/{visit_record_id}_{attachment_id}_{name}
                target_path = os.path.join(user_dir, new_name)
                
                # 复制文件到Appendix目录
                import shutil
                shutil.copy2(attachment_path, target_path)
                
                # 插入数据库记录
                cursor.execute('''
                    INSERT INTO attachment_records (visit_record_id, file_path)
                    VALUES (?, ?)
                ''', (visit_record_id, target_path))
                
                print(f"成功处理附件: {original_name} -> {new_name}")
                attachment_id += 1
                
            except Exception as e:
                print(f"处理附件失败 {attachment_path}: {e}")
                continue

    def get_user_visit_records(self, user_name: str) -> List[Dict]:
        """
        获取用户的所有就诊记录
        
        Args:
            user_name: 用户名
            
        Returns:
            就诊记录列表，每个记录为字典格式
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return []
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询所有就诊记录，按就诊记录ID升序排列
            cursor.execute('''
                SELECT visit_record_id, date, hospital, department, doctor, 
                       organ_system, reason, diagnosis, medication, remark,
                       created_at, updated_at
                FROM visit_records 
                ORDER BY visit_record_id ASC
            ''')
            
            records = []
            for row in cursor.fetchall():
                record = {
                    'visit_record_id': row[0],
                    'date': row[1],
                    'hospital': row[2],
                    'department': row[3],
                    'doctor': row[4],
                    'organ_system': row[5],
                    'reason': row[6],
                    'diagnosis': row[7],
                    'medication': row[8],
                    'remark': row[9],
                    'created_at': row[10],
                    'updated_at': row[11]
                }
                records.append(record)
            
            conn.close()
            return records
            
        except Exception as e:
            print(f"查询用户就诊记录失败: {e}")
            return []

    def get_visit_record_by_id(self, user_name: str, visit_record_id: int) -> Optional[Dict]:
        """
        根据ID获取单个就诊记录
        
        Args:
            user_name: 用户名
            visit_record_id: 就诊记录ID
            
        Returns:
            就诊记录字典，如果未找到则返回None
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return None
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 查询指定ID的就诊记录
            cursor.execute('''
                SELECT visit_record_id, date, hospital, department, doctor, 
                       organ_system, reason, diagnosis, medication, remark,
                       created_at, updated_at
                FROM visit_records 
                WHERE visit_record_id = ?
            ''', (visit_record_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                record = {
                    'visit_record_id': row[0],
                    'date': row[1],
                    'hospital': row[2],
                    'department': row[3],
                    'doctor': row[4],
                    'organ_system': row[5],
                    'reason': row[6],
                    'diagnosis': row[7],
                    'medication': row[8],
                    'remark': row[9],
                    'created_at': row[10],
                    'updated_at': row[11]
                }
                return record
            else:
                return None
                
        except Exception as e:
            print(f"查询就诊记录失败: {e}")
            return None

    def update_visit_record(self, visit_data: Dict) -> bool:
        """
        更新就诊记录
        
        Args:
            visit_data: 包含就诊信息的字典，必须包含visit_record_id和user_name，格式如下：
            {
                'user_name': '用户名',
                'visit_record_id': 记录ID,
                'date': '就诊日期',
                'hospital': '医院名称',
                'department': '科室名称',
                'doctor': '医生名称',
                'organ_system': '器官系统',
                'reason': '就诊原因',
                'diagnosis': '诊断结果',
                'medication': '用药情况',
                'remark': '备注'
            }
            
        Returns:
            是否更新成功
        """
        try:
            user_name = visit_data.get('user_name')
            visit_record_id = visit_data.get('visit_record_id')
            
            if not user_name or not visit_record_id:
                print("错误：缺少用户名或记录ID")
                return False
            
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                print(f"错误：用户 {user_name} 的数据库不存在")
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 更新就诊记录
            cursor.execute('''
                UPDATE visit_records SET
                    date = ?, hospital = ?, department = ?, doctor = ?, 
                    organ_system = ?, reason = ?, diagnosis = ?, 
                    medication = ?, remark = ?, updated_at = CURRENT_TIMESTAMP
                WHERE visit_record_id = ?
            ''', (
                visit_data.get('date', None),
                visit_data.get('hospital', None),
                visit_data.get('department', None),
                visit_data.get('doctor', None),
                visit_data.get('organ_system', None),
                visit_data.get('reason', None),
                visit_data.get('diagnosis', None),
                visit_data.get('medication', None),
                visit_data.get('remark', None),
                visit_record_id
            ))
            
            # 检查是否有记录被更新
            if cursor.rowcount == 0:
                print(f"错误：未找到ID为 {visit_record_id} 的记录")
                conn.close()
                return False
            
            conn.commit()
            conn.close()
            
            print(f"成功更新就诊记录，记录ID: {visit_record_id}")
            return True
            
        except Exception as e:
            print(f"更新就诊记录失败: {e}")
            return False
