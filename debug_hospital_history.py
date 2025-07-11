#!/usr/bin/env python3
"""
调试脚本：测试医院名称历史数据获取功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.data_storage import DataStorage

def test_hospital_history():
    """测试医院历史数据获取"""
    print("=== 医院历史数据调试 ===")
    
    data_storage = DataStorage()
    
    # 获取所有用户
    users = data_storage.get_all_users()
    print(f"发现用户: {users}")
    
    if not users:
        print("⚠️ 没有找到任何用户！请先创建用户并添加就诊记录。")
        return
    
    # 对每个用户测试历史医院数据
    for user in users:
        print(f"\n--- 用户: {user} ---")
        
        # 获取所有就诊记录
        records = data_storage.get_user_visit_records(user)
        print(f"就诊记录数量: {len(records)}")
        
        if records:
            print("前3条记录的医院名称:")
            for i, record in enumerate(records[:3]):
                print(f"  {i+1}. {record.get('hospital', 'N/A')}")
        
        # 测试历史医院名称获取
        hospitals = data_storage.get_history_hospitals(user, 5)
        print(f"历史医院名称 (前5个): {hospitals}")
        
        if not hospitals:
            print("⚠️ 没有找到历史医院名称！")
        else:
            print("✅ 成功获取历史医院名称")

def create_test_data():
    """创建测试数据"""
    print("\n=== 创建测试数据 ===")
    
    data_storage = DataStorage()
    
    # 创建测试用户
    test_user = "测试用户"
    if data_storage.create_user(test_user):
        print(f"✅ 创建测试用户: {test_user}")
    
    # 添加测试就诊记录
    test_records = [
        {
            'user_name': test_user,
            'date': '2024-01-15',
            'hospital': '北京协和医院',
            'department': '内科',
            'doctor': '张医生',
            'organ_system': '心血管',
            'reason': '胸闷',
            'diagnosis': '心律不齐',
            'medication': '美托洛尔',
            'remark': '定期复查',
            'attachment_paths': []
        },
        {
            'user_name': test_user,
            'date': '2024-01-20',
            'hospital': '中日友好医院',
            'department': '外科',
            'doctor': '李医生',
            'organ_system': '消化系统',
            'reason': '腹痛',
            'diagnosis': '急性胃炎',
            'medication': '奥美拉唑',
            'remark': '注意饮食',
            'attachment_paths': []
        },
        {
            'user_name': test_user,
            'date': '2024-01-25',
            'hospital': '北京同仁医院',
            'department': '眼科',
            'doctor': '王医生',
            'organ_system': '五官',
            'reason': '视力下降',
            'diagnosis': '近视',
            'medication': '无',
            'remark': '配眼镜',
            'attachment_paths': []
        }
    ]
    
    success_count = 0
    for record in test_records:
        if data_storage.upload_visit_record(record):
            success_count += 1
            print(f"✅ 添加测试记录: {record['hospital']}")
        else:
            print(f"❌ 添加测试记录失败: {record['hospital']}")
    
    print(f"成功添加 {success_count}/{len(test_records)} 条测试记录")

if __name__ == "__main__":
    print("选择操作:")
    print("1. 测试现有数据")
    print("2. 创建测试数据")
    print("3. 创建测试数据后测试")
    
    choice = input("请选择 (1/2/3): ").strip()
    
    if choice == "1":
        test_hospital_history()
    elif choice == "2":
        create_test_data()
    elif choice == "3":
        create_test_data()
        test_hospital_history()
    else:
        print("无效选择") 