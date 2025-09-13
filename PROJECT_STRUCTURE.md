# Granola 项目结构

```
granola-lite/
├── app/                          # 应用主目录
│   ├── __init__.py
│   ├── main.py                   # FastAPI应用入口
│   ├── config.py                 # 配置管理
│   ├── 
│   ├── api/                      # API路由
│   │   ├── __init__.py
│   │   ├── v1/                   # API v1版本
│   │   │   ├── __init__.py
│   │   │   ├── api.py           # API路由汇总
│   │   │   ├── endpoints/        # API端点
│   │   │   │   ├── __init__.py
│   │   │   │   ├── meetings.py   # 会议相关API
│   │   │   │   ├── transcriptions.py # 转录API
│   │   │   │   ├── notes.py      # 笔记API
│   │   │   │   ├── templates.py  # 模板API
│   │   │   │   └── conversations.py # 对话API
│   │   │   └── deps.py          # API依赖
│   │   
│   ├── core/                     # 核心功能
│   │   ├── __init__.py
│   │   ├── security.py           # 安全相关
│   │   └── exceptions.py         # 自定义异常
│   │   
│   ├── crud/                     # 数据库操作
│   │   ├── __init__.py
│   │   ├── base.py              # 基础CRUD
│   │   ├── meeting.py           # 会议CRUD
│   │   ├── transcription.py     # 转录CRUD
│   │   ├── note.py              # 笔记CRUD
│   │   ├── template.py          # 模板CRUD
│   │   └── conversation.py      # 对话CRUD
│   │   
│   ├── db/                       # 数据库相关
│   │   ├── __init__.py
│   │   ├── base.py              # 数据库基类
│   │   ├── session.py           # 数据库会话
│   │   └── init_db.py           # 数据库初始化
│   │   
│   ├── models/                   # SQLAlchemy模型
│   │   ├── __init__.py
│   │   ├── meeting.py           # 会议模型
│   │   ├── transcription.py     # 转录模型
│   │   ├── note.py              # 笔记模型
│   │   ├── template.py          # 模板模型
│   │   └── conversation.py      # 对话模型
│   │   
│   ├── schemas/                  # Pydantic模式
│   │   ├── __init__.py
│   │   ├── meeting.py           # 会议模式
│   │   ├── transcription.py     # 转录模式
│   │   ├── note.py              # 笔记模式
│   │   ├── template.py          # 模板模式
│   │   └── conversation.py      # 对话模式
│   │   
│   ├── services/                 # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── ai/                  # AI相关服务
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # AI基础抽象类 ✅
│   │   │   ├── openai_provider.py # OpenAI实现 ✅
│   │   │   └── ai_service.py    # AI服务管理器 ✅
│   │   ├── meeting.py           # 会议业务逻辑
│   │   ├── transcription.py     # 转录业务逻辑
│   │   ├── note.py              # 笔记业务逻辑
│   │   └── audio.py             # 音频处理服务
│   │   
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       ├── file_utils.py        # 文件工具
│       └── audio_utils.py       # 音频工具
│
├── alembic/                      # 数据库迁移
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── tests/                        # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   └── test_services/
│
├── uploads/                      # 上传文件目录
│   ├── audio/
│   └── temp/
│
├── .env.example                  # 环境变量模板 ✅
├── .env                         # 环境变量(需要创建)
├── .gitignore                   
├── requirements.txt             # 依赖列表 ✅
├── database_design.md           # 数据库设计文档 ✅
├── PROJECT_STRUCTURE.md         # 项目结构说明 ✅
└── README.md                    # 项目说明
```

## 已完成的模块
- ✅ 数据库设计文档
- ✅ AI抽象接口
- ✅ OpenAI API集成
- ✅ 基础项目结构
- ✅ 配置管理

## 待开发的模块
- 数据库ORM模型
- 数据库连接和初始化
- API路由和端点
- 业务逻辑服务
- 音频处理
- 错误处理和日志
- 测试和文档

## 启动项目

1. 复制环境变量模板
```bash
cp .env.example .env
```

2. 编辑.env文件，配置OpenAI API密钥等

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 启动开发服务器
```bash
cd app
python main.py
```

或使用uvicorn：
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```