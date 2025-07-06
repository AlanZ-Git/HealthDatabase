# 个人健康档案管理

本项目是为了管理自己的日常就诊、用药记录，方便梳理个人的健康状况

用sqlite管理数据

UI支持录入就诊记录，查看附件，支持导出就诊记录的附件

## 数据库设计

### 就诊记录表
这是一个用户的就诊记录总表，名称为 visit_records

```SQL
CREATE TABLE visit_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT COMMENT '就诊记录ID',
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

### 附件表
这是一个用户所有上传附件的记录表，名称为 attachment_records

```SQL
CREATE TABLE attachment_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT COMMENT '附件ID',
    visit_record_id INTEGER NOT NULL COMMENT '就诊记录ID',
    file_path TEXT NOT NULL COMMENT '附件文件路径',
    FOREIGN KEY (visit_record_id) REFERENCES visit_records(id) ON DELETE CASCADE
);
```

