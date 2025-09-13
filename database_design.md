# Granola 数据库设计

## 核心表结构

### 1. meetings (会议表)
```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    status VARCHAR(50) DEFAULT 'active', -- active, completed, cancelled
    template_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);
```

### 2. transcriptions (转录表)
```sql
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    speaker VARCHAR(100),
    start_time FLOAT, -- 相对会议开始的秒数
    end_time FLOAT,
    confidence FLOAT, -- 转录置信度
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);
```

### 3. notes (笔记表)
```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    original_content TEXT, -- AI增强前的原始内容
    position INTEGER DEFAULT 0, -- 笔记在会议中的位置顺序
    timestamp FLOAT, -- 相对会议开始的时间点
    is_ai_enhanced BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);
```

### 4. templates (模板表)
```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100), -- 1on1, retrospective, interview, sales等
    structure JSON, -- 模板结构定义
    prompt_template TEXT, -- AI处理时使用的提示模板
    is_default BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5. conversations (AI对话表)
```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    context_used TEXT, -- 使用的会议上下文
    model_used VARCHAR(100), -- 使用的AI模型
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);
```

### 6. audio_files (音频文件表)
```sql
CREATE TABLE audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    duration FLOAT, -- 音频时长(秒)
    format VARCHAR(50), -- wav, mp3, m4a等
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
);
```

## 索引设计
```sql
-- 会议查询优化
CREATE INDEX idx_meetings_start_time ON meetings(start_time);
CREATE INDEX idx_meetings_status ON meetings(status);

-- 转录内容查询优化
CREATE INDEX idx_transcriptions_meeting_id ON transcriptions(meeting_id);
CREATE INDEX idx_transcriptions_time_range ON transcriptions(meeting_id, start_time, end_time);

-- 笔记查询优化
CREATE INDEX idx_notes_meeting_id ON notes(meeting_id);
CREATE INDEX idx_notes_position ON notes(meeting_id, position);

-- 对话查询优化
CREATE INDEX idx_conversations_meeting_id ON conversations(meeting_id);

-- 音频文件查询优化
CREATE INDEX idx_audio_files_meeting_id ON audio_files(meeting_id);
```

## 数据关系说明

1. **一对多关系**：
   - 一个会议可以有多条转录记录
   - 一个会议可以有多条笔记
   - 一个会议可以有多次AI对话
   - 一个会议可以有多个音频文件

2. **模板关系**：
   - 会议可以基于模板创建，但模板删除不影响已创建的会议

3. **级联删除**：
   - 删除会议时，相关的转录、笔记、对话、音频文件都会被删除

## 预设数据

### 默认模板
1. **一对一会议模板**
2. **团队回顾会议模板**  
3. **面试会议模板**
4. **销售会议模板**
5. **项目讨论模板**