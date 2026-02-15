# 个人健康档案管理系统

一个基于 PyQt6 的个人就诊记录数据管理软件，帮助用户系统化管理日常就诊、用药记录，方便梳理个人健康状况。

## 项目概述

本项目采用 Python + PyQt6 + SQLite 技术栈，提供直观的 GUI 界面用于个人医疗信息的录入、查看和管理。软件支持多用户数据隔离，确保个人隐私安全。

**核心特点：**
- 🏥 完整的就诊记录管理
- 📎 医疗附件上传和存储
- 🔍 灵活的数据筛选和查看
- 📤 选择性数据导出功能
- 👤 多用户数据隔离
- 🔒 本地数据存储，隐私安全

## 功能特性

### 数据录入与管理
- 支持录入完整的就诊信息（日期、医院、科室、医生、诊断等）
- 按器官系统分类管理医疗记录
- 用药信息和备注信息管理

### 附件上传处理
- 支持上传病例扫描件、检查报告等附件
- 自动化文件命名和存储管理
- 附件与就诊记录关联存储

### 筛选查看功能
- 多维度数据筛选（日期、医院、科室等）
- 表格形式直观展示就诊记录
- 附件预览和管理功能

### 数据导出功能
- 选定记录的附件批量导出
- 灵活的导出选项配置

## 安装使用

### 快速开始（预编译版本）

1. 从 [GitHub Releases](../../releases) 下载最新版本
2. 解压缩到任意目录
3. 运行 `就诊信息管理.exe` 即可使用

**系统要求：** Windows 10/11

### 源码编译

#### 环境依赖
```bash
Python 3.8+
PyQt6 >= 6.7.1
PyQt6-Qt6 >= 6.7.3
PyQt6_sip >= 13.10.2
```

#### 安装步骤
```bash
# 克隆项目
git clone <repository-url>
cd HealthDatabase

# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

#### 编译打包
```bash
# 使用提供的编译脚本
python compile.py
```

编译完成后会在 `dist` 目录生成带版本号的 zip 压缩包。

## 项目结构

```
HealthDatabase/
├── main.py                 # 主程序入口
├── compile.py              # 编译打包脚本
├── requirements.txt        # Python依赖列表
├── settings.ini            # 程序配置文件
├── icon.png               # 程序图标
├── lib/                   # 核心功能模块
│   ├── data_storage.py    # 数据存储层
│   ├── table_viewer.py    # 表格视图组件
│   ├── visit_record_dialog.py  # 就诊记录对话框
│   ├── attachment_dialog.py    # 附件管理对话框
│   ├── export_manager.py       # 导出功能管理
│   ├── settings_manager.py     # 设置管理
│   ├── config_manager.py       # 配置管理
│   ├── ui_components.py        # UI组件库
│   └── table_components.py     # 表格组件
├── user_data/             # 用户数据目录
│   ├── *.sqlite          # SQLite数据库文件
│   └── appendix/          # 附件存储目录
│       └── {user}/       # 按用户分类的附件
```

### 关键文件说明

- **main.py**: 程序主入口，包含主界面逻辑
- **lib/data_storage.py**: 数据库操作封装，负责 SQLite 数据存储
- **lib/table_viewer.py**: 数据表格展示组件
- **compile.py**: 自动化编译脚本，支持版本管理和资源打包

## 数据库设计

### 就诊记录表 (visit_records)
```sql
CREATE TABLE visit_records (
    visit_record_id INTEGER PRIMARY KEY AUTOINCREMENT COMMENT '就诊记录ID',
    date TEXT NOT NULL COMMENT '就诊日期',
    hospital TEXT COMMENT '医院名称',
    department TEXT COMMENT '科室名称',
    doctor TEXT COMMENT '医生名称',
    organ_system TEXT COMMENT '器官系统',
    reason TEXT COMMENT '症状事由',
    diagnosis TEXT COMMENT '诊断结果',
    medication TEXT COMMENT '用药信息',
    remark TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间'
);
```

### 附件表 (attachment_records)
```sql
CREATE TABLE attachment_records (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_record_id INTEGER NOT NULL,     -- 关联就诊记录ID
    file_path TEXT NOT NULL,              -- 附件文件路径
    FOREIGN KEY (visit_record_id) REFERENCES visit_records(id) ON DELETE CASCADE
);
```

## 开发指南

### Fork 和自定义修改

本项目采用模块化设计，支持灵活的功能扩展和自定义：

1. **Fork 项目**：点击右上角 Fork 按钮创建自己的副本
2. **功能扩展**：在 `lib/` 目录下添加新的功能模块
3. **界面定制**：修改 `lib/ui_components.py` 中的 UI 组件
4. **数据结构扩展**：修改 `lib/data_storage.py` 中的数据库操作

### 贡献指南

欢迎提交 Issue 和 Pull Request：

1. 提交 Issue 描述问题或功能需求
2. Fork 项目并创建功能分支
3. 提交代码前请确保：
   - 代码符合项目规范
   - 添加必要的注释
   - 测试功能正常
4. 提交 Pull Request

### 开发环境配置

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试（如有）
python -m pytest

# 代码格式化（推荐）
pip install black
black .
```

## 隐私与安全

- ✅ 数据完全存储在本地，不上传云端
- ✅ 支持多用户数据隔离
- ✅ 附件文件本地加密存储
- ✅ 无网络连接要求，离线使用

## 版本历史

查看 [Releases](../../releases) 页面获取详细的版本更新记录。

## 许可证

本项目采用 MIT License，详情请查看 [LICENSE](LICENSE) 文件。

## 支持与反馈

如遇问题或有改进建议，请：

1. 查看 [Issues](../../issues) 中是否有类似问题
2. 创建新的 Issue 描述问题
3. 提供详细的错误信息和复现步骤

---

**注意**：本软件仅用于个人健康信息管理，不能替代专业医疗建议。重要医疗决策请咨询专业医护人员。