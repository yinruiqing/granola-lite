# Granola Lite - AI 会议纪要工具后端

基于 FastAPI + SQLite + OpenAI 的会议纪要工具后端实现，复现了 Granola 的核心功能。

## 🌟 核心功能

### 1. AI 增强转录
- **实时音频转录** - 使用 OpenAI Whisper API 进行语音转文字
- **多格式音频支持** - 支持 WAV、MP3、M4A、FLAC 等格式
- **WebSocket 流式转录** - 实时转录音频流
- **说话人识别** - 区分不同发言人

### 2. 交互式笔记
- **手动笔记记录** - 用户可以实时记录要点
- **AI 内容增强** - 结合转录内容智能扩展笔记
- **版本对比** - 支持查看增强前后的内容对比
- **智能排序** - 支持笔记重新排序和组织

### 3. 智能模板系统
- **预设模板** - 一对一、回顾会、面试、销售等场景模板
- **自定义模板** - 支持创建专属会议模板
- **结构化输出** - 基于模板生成结构化纪要
- **模板管理** - 完整的模板 CRUD 操作

### 4. AI 智能问答
- **上下文问答** - 基于会议内容回答问题
- **建议问题** - AI 自动生成相关问题
- **批量提问** - 支持一次询问多个问题
- **对话历史** - 保存和管理问答记录

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI** - 现代化的 Python Web 框架
- **SQLAlchemy** - 异步 ORM 数据库操作
- **SQLite** - 轻量级数据库
- **OpenAI API** - Whisper STT + GPT LLM
- **Pydantic** - 数据验证和序列化
- **Loguru** - 结构化日志系统

### 项目结构
```
app/
├── api/v1/endpoints/     # API 端点
├── core/                 # 核心功能 (异常、日志、中间件)
├── db/                   # 数据库连接和初始化
├── models/               # SQLAlchemy 数据模型
├── schemas/              # Pydantic 数据模式
├── services/             # 业务逻辑服务
│   └── ai/              # AI 服务抽象层
└── utils/                # 工具函数
```

### API 模块
- **🎵 Audio** - 音频文件上传和处理
- **📝 Transcriptions** - 语音转录和 WebSocket 流式转录
- **📋 Notes** - 笔记的 CRUD 和搜索
- **🤖 AI Enhancement** - AI 笔记增强和对比
- **📄 Templates** - 会议模板管理
- **💬 Conversations** - AI 问答对话
- **🏢 Meetings** - 会议生命周期管理

## 🚀 快速开始

### 环境要求
- Python 3.8+
- OpenAI API Key

### 安装运行

1. **克隆项目**
```bash
git clone <repository-url>
cd granola-lite
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境**
```bash
cp .env.example .env
# 编辑 .env 文件，配置 OpenAI API Key
```

4. **启动服务**
```bash
python start.py
```

5. **访问 API 文档**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 环境变量配置

```env
# OpenAI 配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
WHISPER_MODEL=whisper-1

# 服务配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./granola.db

# 文件存储
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600  # 100MB

# 安全配置
SECRET_KEY=your-secret-key-change-this-in-production
```

## 📖 API 使用示例

### 1. 创建会议
```bash
curl -X POST "http://localhost:8000/api/v1/meetings/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "团队周会",
    "description": "讨论本周工作进展",
    "template_id": 1
  }'
```

### 2. 上传音频文件
```bash
curl -X POST "http://localhost:8000/api/v1/audio/upload/1" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@meeting.wav"
```

### 3. 转录音频
```bash
curl -X POST "http://localhost:8000/api/v1/transcriptions/transcribe" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_id": 1,
    "language": "zh"
  }'
```

### 4. 创建笔记
```bash
curl -X POST "http://localhost:8000/api/v1/notes/" \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_id": 1,
    "content": "讨论了产品路线图",
    "timestamp": 120.5
  }'
```

### 5. AI 增强笔记
```bash
curl -X POST "http://localhost:8000/api/v1/ai/notes/1/enhance" \
  -H "Content-Type: application/json" \
  -d '{
    "use_template": true
  }'
```

### 6. AI 问答
```bash
curl -X POST "http://localhost:8000/api/v1/conversations/meetings/1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "这次会议讨论的主要决策是什么？"
  }'
```

## 🔧 高级功能

### WebSocket 实时转录
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/transcriptions/stream/1');

// 发送初始化消息
ws.send(JSON.stringify({
  type: 'init',
  sample_rate: 16000,
  language: 'zh'
}));

// 发送音频数据
ws.send(JSON.stringify({
  type: 'audio',
  data: base64AudioData
}));
```

### 批量操作
- 批量增强笔记
- 批量提问
- 批量会议操作

### 健康监控
- 基础健康检查: `/health`
- 详细系统监控: `/health/detailed`

## 🎯 核心特性

### AI 服务抽象层
- **多服务商支持** - 可轻松切换 OpenAI、Claude、本地模型
- **统一接口** - STT 和 LLM 的抽象基类
- **配置化** - 通过配置文件管理不同的 AI 服务

### 中间件系统
- **请求日志** - 详细记录 API 调用
- **异常处理** - 统一的错误处理和响应
- **安全头** - 自动添加安全响应头
- **速率限制** - 防止 API 滥用

### 数据验证
- **输入验证** - Pydantic 模式验证
- **类型安全** - 完整的类型提示
- **错误友好** - 清晰的验证错误信息

## 🔍 监控和日志

### 日志系统
- **结构化日志** - 使用 Loguru 进行日志记录
- **分类日志** - API、服务、AI、数据库分类记录
- **日志轮转** - 自动日志轮转和压缩

### 健康检查
- 数据库连接检查
- AI 服务可用性检查
- 存储空间监控
- 系统资源监控

## 🤝 扩展开发

### 添加新的 AI 服务商

1. **实现服务商类**
```python
class AnthropicLLMProvider(LLMProvider):
    def _get_provider_name(self) -> AIProvider:
        return AIProvider.ANTHROPIC
    
    async def chat_completion(self, messages, **kwargs):
        # 实现 Anthropic API 调用
        pass
```

2. **注册服务商**
```python
AIServiceFactory.register_llm_provider(
    AIProvider.ANTHROPIC, 
    AnthropicLLMProvider
)
```

### 添加新的 API 端点

1. **创建服务类** - 在 `services/` 目录
2. **定义数据模式** - 在 `schemas/` 目录  
3. **实现 API 端点** - 在 `api/v1/endpoints/` 目录
4. **注册路由** - 在 `api/v1/api.py` 中

## 🐛 开发调试

### 日志查看
```bash
# 实时查看所有日志
tail -f logs/granola.log

# 查看错误日志
tail -f logs/granola_error.log

# 查看 AI 服务日志
tail -f logs/ai_service.log
```

### 数据库操作
```bash
# 初始化数据库
python -c "import asyncio; from app.db.init_db import init_database; asyncio.run(init_database())"

# 查看数据库
sqlite3 granola.db ".tables"
```

## 📝 TODO 和路线图

- [ ] 用户认证和权限管理
- [ ] 数据库迁移脚本
- [ ] Docker 容器化
- [ ] 单元测试覆盖
- [ ] API 限流优化
- [ ] 缓存层集成
- [ ] 更多 AI 服务商支持
- [ ] 前端 Web 界面

## 📄 许可证

MIT License

## 🙏 致谢

本项目复现了 [Granola](https://granola.ai) 的核心功能，致敬原创团队的优秀设计理念。

---

**开发完成** ✅ 后端核心功能已全部实现，包括 4 个核心模块的完整 API 和完善的错误处理、日志系统。