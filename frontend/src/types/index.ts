// 会议相关类型
export interface Meeting {
  id: number;
  title: string;
  description?: string;
  status: 'scheduled' | 'in_progress' | 'completed';
  template_id?: number;
  created_at: string;
  updated_at: string;
}

// 转录相关类型
export interface Transcription {
  id: number;
  meeting_id: number;
  content: string;
  language: string;
  speaker?: string;
  timestamp: number;
  created_at: string;
}

// 笔记相关类型
export interface Note {
  id: number;
  meeting_id: number;
  content: string;
  original_content?: string;
  enhanced_content?: string;
  timestamp?: number;
  created_at: string;
  updated_at: string;
}

// 模板相关类型
export interface Template {
  id: number;
  name: string;
  description?: string;
  category: 'meeting' | 'notes' | 'summary' | 'action_items';
  structure: TemplateStructure;
  is_active: boolean;
  is_default?: boolean;
  created_at: string;
  updated_at: string;
}

export interface TemplateStructure {
  title?: string;
  sections: TemplateSection[];
  variables?: Record<string, string>;
}

export interface TemplateSection {
  id: string;
  title: string;
  type: 'text' | 'list' | 'table' | 'markdown';
  content?: string;
  placeholder?: string;
  required?: boolean;
  order: number;
}

// 对话相关类型
export interface Conversation {
  id: number;
  meeting_id: number;
  question: string;
  answer: string;
  created_at: string;
}

// API 响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

// 音频相关类型
export interface AudioFile {
  id: number;
  meeting_id: number;
  filename: string;
  file_path: string;
  file_size: number;
  duration?: number;
  format: string;
  created_at: string;
}

// 设置相关类型
export interface UserSettings {
  // 通用设置
  language: 'zh' | 'en';
  theme: 'light' | 'dark' | 'system';
  timezone: string;
  
  // 会议设置
  defaultMeetingDuration: number; // 分钟
  autoSaveInterval: number; // 秒
  enableNotifications: boolean;
  
  // AI 设置
  ai: {
    provider: 'openai' | 'claude' | 'local';
    apiKey?: string;
    baseUrl?: string;
    model: string;
    temperature: number;
    maxTokens: number;
  };
  
  // 转录设置
  transcription: {
    language: string;
    autoDetectLanguage: boolean;
    enablePunctuation: boolean;
    enableFiltering: boolean;
  };
  
  // 导出设置
  export: {
    defaultFormat: 'markdown' | 'pdf' | 'docx' | 'txt';
    includeTimestamps: boolean;
    includeMetadata: boolean;
  };
  
  // 隐私设置
  privacy: {
    enableAnalytics: boolean;
    enableCrashReporting: boolean;
    dataRetentionDays: number;
  };
}

export interface SettingsCategory {
  id: string;
  title: string;
  description: string;
  icon: any;
  settings: SettingField[];
}

export interface SettingField {
  key: string;
  type: 'text' | 'password' | 'number' | 'boolean' | 'select' | 'textarea';
  label: string;
  description?: string;
  placeholder?: string;
  options?: { label: string; value: any }[];
  min?: number;
  max?: number;
  step?: number;
  required?: boolean;
  sensitive?: boolean; // 敏感信息，如API密钥
}

