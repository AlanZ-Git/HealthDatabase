import sqlite3
import os
import glob
from typing import List, Dict, Optional
from contextlib import contextmanager


class DataStorage:
    """数据库存储管理类，负责所有数据库操作"""
    
    # 默认配置
    DEFAULT_DATA_DIR = 'data'
    DEFAULT_APPENDIX_DIR = 'Appendix'
    MAX_FILENAME_LENGTH = 100
    
    def __init__(self, data_dir: Optional[str] = None, appendix_dir: Optional[str] = None):
        """
        初始化数据存储管理器
        
        Args:
            data_dir: 数据文件目录
            appendix_dir: 附件目录
        """
        self.data_dir = data_dir or self.DEFAULT_DATA_DIR
        self.appendix_dir = appendix_dir or self.DEFAULT_APPENDIX_DIR
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def _get_db_path(self, user_name: str) -> str:
        """获取用户数据库文件路径"""
        return os.path.join(self.data_dir, f'{user_name}.sqlite')
    
    @contextmanager
    def _db_connection(self, user_name: str):
        """
        数据库连接上下文管理器
        
        Args:
            user_name: 用户名
            
        Yields:
            数据库连接对象
        """
        db_path = self._get_db_path(user_name)
        if not os.path.exists(db_path):
            yield None
            return
            
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _execute_query(self, user_name: str, query: str, params: tuple = ()) -> List[tuple]:
        """
        执行查询语句的通用方法
        
        Args:
            user_name: 用户名
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        try:
            with self._db_connection(user_name) as conn:
                if conn is None:
                    return []
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"查询执行失败: {e}")
            return []
    
    def _execute_update(self, user_name: str, query: str, params: tuple = ()) -> bool:
        """
        执行更新语句的通用方法
        
        Args:
            user_name: 用户名
            query: SQL更新语句
            params: 更新参数
            
        Returns:
            是否执行成功
        """
        try:
            with self._db_connection(user_name) as conn:
                if conn is None:
                    return False
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            print(f"更新执行失败: {e}")
            return False

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
    
    def _get_history_field(self, user_name: str, field: str, hospital_filter: Optional[str] = None, limit: int = 5) -> List[str]:
        """
        获取用户历史输入字段的通用方法
        
        Args:
            user_name: 用户名
            field: 要查询的字段名（hospital, department, doctor）
            hospital_filter: 医院筛选条件，仅对department和doctor有效
            limit: 返回结果数量限制，默认5个
            
        Returns:
            字段值列表，按从新到旧排序
        """
        # 如果科室或医生查询但医院名称为空（None或空字符串），返回空列表
        if field in ['department', 'doctor'] and (hospital_filter is None or not hospital_filter.strip()):
            return []
        
        if hospital_filter and hospital_filter.strip() and field in ['department', 'doctor']:
            # 按医院筛选，获取每个字段值的最新记录
            query = f'''
                SELECT {field}
                FROM visit_records 
                WHERE {field} IS NOT NULL AND {field} != '' 
                AND hospital = ?
                GROUP BY {field}
                ORDER BY MAX(created_at) DESC
                LIMIT ?
            '''
            params = (hospital_filter, limit)
        else:
            # 查询所有值，获取每个字段值的最新记录
            query = f'''
                SELECT {field}
                FROM visit_records 
                WHERE {field} IS NOT NULL AND {field} != ''
                GROUP BY {field}
                ORDER BY MAX(created_at) DESC
                LIMIT ?
            '''
            params = (limit,)
        
        results = self._execute_query(user_name, query, params)
        return [row[0] for row in results]

    def get_history_hospitals(self, user_name: str, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的医院名称
        
        Args:
            user_name: 用户名
            limit: 返回结果数量限制，默认5个
            
        Returns:
            医院名称列表，按从新到旧排序
        """
        return self._get_history_field(user_name, 'hospital', limit=limit)
    
    def get_history_departments(self, user_name: str, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的科室名称
        
        Args:
            user_name: 用户名
            limit: 返回结果数量限制，默认5个
            
        Returns:
            科室名称列表，按从新到旧排序
        """
        return self._get_history_field(user_name, 'department', limit=limit)
    
    def get_history_departments_by_hospital(self, user_name: str, hospital: Optional[str] = None, limit: int = 5) -> List[str]:
        """
        获取用户历史输入的科室名称，可按医院筛选
        
        Args:
            user_name: 用户名
            hospital: 医院名称，如果提供则只查询该医院的科室
            limit: 返回结果数量限制，默认5个
            
        Returns:
            科室名称列表，按从新到旧排序
        """
        return self._get_history_field(user_name, 'department', hospital_filter=hospital, limit=limit)
    
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
        return self._get_history_field(user_name, 'doctor', hospital_filter=hospital, limit=limit)
    
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
        # 确保用户附件目录存在
        user_dir = self._ensure_user_attachment_dir(user_name)
        
        attachment_id = 1
        for attachment_path in attachment_paths:
            if not os.path.exists(attachment_path):
                print(f"警告：附件文件不存在: {attachment_path}")
                continue
            
            try:
                # 获取原文件名并生成新文件名
                original_name = os.path.basename(attachment_path)
                new_name = self._generate_attachment_filename(visit_record_id, attachment_id, original_name)
                
                # 构建目标路径
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

    def get_user_visit_records(self, user_name: str, sort_column: str = 'visit_record_id', sort_order: str = 'ASC') -> List[Dict]:
        """
        获取用户的所有就诊记录
        
        Args:
            user_name: 用户名
            sort_column: 排序字段，支持 'visit_record_id' 或 'date'
            sort_order: 排序顺序，'ASC' 或 'DESC'
            
        Returns:
            就诊记录列表，每个记录为字典格式
        """
        # 验证排序参数
        valid_columns = ['visit_record_id', 'date']
        valid_orders = ['ASC', 'DESC']
        
        if sort_column not in valid_columns:
            sort_column = 'visit_record_id'
        if sort_order not in valid_orders:
            sort_order = 'ASC'
        
        # 查询所有就诊记录
        query = f'''
            SELECT visit_record_id, date, hospital, department, doctor, 
                   organ_system, reason, diagnosis, medication, remark,
                   created_at, updated_at
            FROM visit_records 
            ORDER BY {sort_column} {sort_order}
        '''
        
        results = self._execute_query(user_name, query)
        records = []
        for row in results:
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
        
        return records

    def get_visit_record_by_id(self, user_name: str, visit_record_id: int) -> Optional[Dict]:
        """
        根据ID获取单个就诊记录
        
        Args:
            user_name: 用户名
            visit_record_id: 就诊记录ID
            
        Returns:
            就诊记录字典，如果未找到则返回None
        """
        query = '''
            SELECT visit_record_id, date, hospital, department, doctor, 
                   organ_system, reason, diagnosis, medication, remark,
                   created_at, updated_at
            FROM visit_records 
            WHERE visit_record_id = ?
        '''
        
        results = self._execute_query(user_name, query, (visit_record_id,))
        
        if results:
            row = results[0]
            return {
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
        else:
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

    def get_visit_attachments(self, user_name: str, visit_record_id: int) -> List[Dict]:
        """
        获取指定就诊记录的附件列表
        
        Args:
            user_name: 用户名
            visit_record_id: 就诊记录ID
            
        Returns:
            附件列表，每个附件为字典格式 {'attachment_id': int, 'file_path': str, 'file_name': str}
        """
        query = '''
            SELECT attachment_id, file_path
            FROM attachment_records 
            WHERE visit_record_id = ?
            ORDER BY attachment_id ASC
        '''
        
        results = self._execute_query(user_name, query, (visit_record_id,))
        
        attachments = []
        for row in results:
            attachment_id, file_path = row
            file_name = os.path.basename(file_path)
            attachments.append({
                'attachment_id': attachment_id,
                'file_path': file_path,
                'file_name': file_name
            })
        
        return attachments

    def delete_attachment(self, user_name: str, attachment_id: int) -> bool:
        """
        删除指定的附件
        
        Args:
            user_name: 用户名
            attachment_id: 附件ID
            
        Returns:
            是否删除成功
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 先获取文件路径，用于删除物理文件
            cursor.execute('SELECT file_path FROM attachment_records WHERE attachment_id = ?', 
                         (attachment_id,))
            result = cursor.fetchone()
            
            if result:
                file_path = result[0]
                
                # 删除数据库记录
                cursor.execute('DELETE FROM attachment_records WHERE attachment_id = ?', 
                             (attachment_id,))
                
                # 删除物理文件
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"成功删除附件文件: {file_path}")
                    except Exception as e:
                        print(f"删除附件文件失败: {e}")
                
                conn.commit()
                conn.close()
                return True
            else:
                conn.close()
                return False
                
        except Exception as e:
            print(f"删除附件失败: {e}")
            return False

    def delete_visit_record(self, user_name: str, visit_record_id: int) -> bool:
        """
        删除指定的就诊记录及其所有附件
        
        Args:
            user_name: 用户名
            visit_record_id: 就诊记录ID
            
        Returns:
            是否删除成功
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 先获取该记录的所有附件，用于删除物理文件
            cursor.execute('SELECT file_path FROM attachment_records WHERE visit_record_id = ?', 
                         (visit_record_id,))
            attachment_files = cursor.fetchall()
            
            # 删除附件记录
            cursor.execute('DELETE FROM attachment_records WHERE visit_record_id = ?', 
                         (visit_record_id,))
            
            # 删除就诊记录
            cursor.execute('DELETE FROM visit_records WHERE visit_record_id = ?', 
                         (visit_record_id,))
            
            # 检查是否有记录被删除
            if cursor.rowcount == 0:
                print(f"错误：未找到ID为 {visit_record_id} 的就诊记录")
                conn.close()
                return False
            
            # 删除附件的物理文件
            for (file_path,) in attachment_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"成功删除附件文件: {file_path}")
                    except Exception as e:
                        print(f"删除附件文件失败: {e}")
            
            conn.commit()
            conn.close()
            
            print(f"成功删除就诊记录，记录ID: {visit_record_id}")
            return True
            
        except Exception as e:
            print(f"删除就诊记录失败: {e}")
            return False

    def delete_multiple_visit_records(self, user_name: str, visit_record_ids: List[int]) -> int:
        """
        批量删除就诊记录及其所有附件
        
        Args:
            user_name: 用户名
            visit_record_ids: 就诊记录ID列表
            
        Returns:
            成功删除的记录数量
        """
        if not visit_record_ids:
            return 0
            
        success_count = 0
        for visit_record_id in visit_record_ids:
            if self.delete_visit_record(user_name, visit_record_id):
                success_count += 1
        
        return success_count

    def add_attachment_to_visit(self, user_name: str, visit_record_id: int, attachment_path: str) -> bool:
        """
        为指定就诊记录添加单个附件
        
        Args:
            user_name: 用户名
            visit_record_id: 就诊记录ID
            attachment_path: 附件文件路径
            
        Returns:
            是否添加成功
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 处理附件
            self._process_attachments(cursor, visit_record_id, [attachment_path], user_name)
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"添加附件失败: {e}")
            return False

    def update_attachment_path(self, user_name: str, attachment_id: int, new_file_path: str) -> bool:
        """
        更新指定附件，用新文件替换原附件，保持原有命名规则
        
        Args:
            user_name: 用户名
            attachment_id: 附件ID
            new_file_path: 新的源文件路径
            
        Returns:
            是否更新成功
        """
        try:
            db_path = self._get_db_path(user_name)
            if not os.path.exists(db_path):
                return False
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 先获取原附件记录，包括visit_record_id和当前文件路径
            cursor.execute('''
                SELECT visit_record_id, file_path 
                FROM attachment_records 
                WHERE attachment_id = ?
            ''', (attachment_id,))
            
            result = cursor.fetchone()
            if not result:
                print(f"错误：未找到ID为 {attachment_id} 的附件记录")
                conn.close()
                return False
            
            visit_record_id, old_file_path = result
            
            # 获取新文件的基本信息
            new_file_name = os.path.basename(new_file_path)
            name, ext = os.path.splitext(new_file_name)
            
            # 确保附件目录和用户目录存在
            user_dir = os.path.join(self.appendix_dir, user_name)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
            
            # 生成新的文件名，保持原有命名规则：{visit_record_id}_{attachment_id}_{name}
            new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
            
            # 如果新文件名长度超过限制，截断name部分
            if len(new_name) > self.MAX_FILENAME_LENGTH:
                max_name_length = self.MAX_FILENAME_LENGTH - len(str(visit_record_id)) - len(str(attachment_id)) - len(ext) - 2
                if max_name_length > 0:
                    name = name[:max_name_length]
                    new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
                else:
                    # 如果连基本结构都放不下，使用最简单的命名
                    new_name = f"{visit_record_id}_{attachment_id}{ext}"
            
            # 构建新的目标路径
            target_path = os.path.join(user_dir, new_name)
            
            # 删除旧文件（如果存在）
            if old_file_path and os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                    print(f"成功删除旧附件文件: {old_file_path}")
                except Exception as e:
                    print(f"删除旧附件文件失败: {e}")
            
            # 复制新文件到目标位置
            import shutil
            shutil.copy2(new_file_path, target_path)
            print(f"成功复制新附件: {new_file_name} -> {new_name}")
            
            # 更新数据库记录
            cursor.execute('''
                UPDATE attachment_records 
                SET file_path = ? 
                WHERE attachment_id = ?
            ''', (target_path, attachment_id))
            
            conn.commit()
            conn.close()
            
            print(f"成功更新附件，附件ID: {attachment_id}, 新路径: {target_path}")
            return True
            
        except Exception as e:
            print(f"更新附件失败: {e}")
            return False

    def _ensure_user_attachment_dir(self, user_name: str) -> str:
        """
        确保用户附件目录存在并返回路径
        
        Args:
            user_name: 用户名
            
        Returns:
            用户附件目录路径
        """
        # 确保附件目录存在
        if not os.path.exists(self.appendix_dir):
            os.makedirs(self.appendix_dir)
        
        # 确保用户目录存在
        user_dir = os.path.join(self.appendix_dir, user_name)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        return user_dir
    
    def _generate_attachment_filename(self, visit_record_id: int, attachment_id: int, original_name: str) -> str:
        """
        生成附件文件名
        
        Args:
            visit_record_id: 就诊记录ID
            attachment_id: 附件ID
            original_name: 原始文件名
            
        Returns:
            新的文件名
        """
        name, ext = os.path.splitext(original_name)
        new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
        
        # 如果新文件名长度超过限制，截断name部分
        if len(new_name) > self.MAX_FILENAME_LENGTH:
            max_name_length = self.MAX_FILENAME_LENGTH - len(str(visit_record_id)) - len(str(attachment_id)) - len(ext) - 2
            if max_name_length > 0:
                name = name[:max_name_length]
                new_name = f"{visit_record_id}_{attachment_id}_{name}{ext}"
            else:
                # 如果连基本结构都放不下，使用最简单的命名
                new_name = f"{visit_record_id}_{attachment_id}{ext}"
        
        return new_name
