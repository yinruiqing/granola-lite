"""
应用配置管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, Dict, Any
import os
from pathlib import Path

# AI配置相关的类将在需要时动态导入以避免循环依赖


class Settings(BaseSettings):
    """应用配置"""
    
    # 基本配置
    app_name: str = "Granola Meeting Notes API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="调试模式")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", description="服务器地址")
    port: int = Field(default=8000, description="服务器端口")
    
    # 数据库配置
    database_url: str = Field(
        default="sqlite+aiosqlite:///./granola.db", 
        description="数据库连接URL"
    )
    database_echo: bool = Field(default=False, description="SQL语句调试输出")
    database_pool_size: int = Field(default=10, description="连接池大小")
    database_max_overflow: int = Field(default=20, description="连接池最大溢出")
    
    # Redis配置
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis连接URL")
    
    # AI服务配置
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API密钥")
    openai_base_url: Optional[str] = Field(default=None, description="OpenAI API基础URL")
    openai_model: str = Field(default="gpt-4o-mini", description="默认OpenAI模型")
    whisper_model: str = Field(default="whisper-1", description="默认Whisper模型")
    
    # 代理配置
    http_proxy: Optional[str] = Field(default=None, description="HTTP代理地址")
    https_proxy: Optional[str] = Field(default=None, description="HTTPS代理地址")
    proxy_auth: Optional[str] = Field(default=None, description="代理认证信息 (username:password)")
    
    # 文件存储配置
    upload_dir: str = Field(default="uploads", description="上传文件目录")
    max_file_size: int = Field(default=100 * 1024 * 1024, description="最大文件大小(100MB)")
    allowed_audio_types: list = Field(
        default=["audio/wav", "audio/mp3", "audio/m4a", "audio/flac"],
        description="允许的音频文件类型"
    )
    
    # AWS S3配置
    aws_access_key_id: Optional[str] = Field(default=None, description="AWS访问密钥ID")
    aws_secret_access_key: Optional[str] = Field(default=None, description="AWS秘密访问密钥")
    aws_s3_bucket_name: Optional[str] = Field(default=None, description="S3存储桶名称")
    aws_region: str = Field(default="us-east-1", description="AWS区域")
    
    # 安全配置
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        description="JWT密钥"
    )
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    
    # CORS配置
    allowed_origins: list = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="允许的跨域源"
    )
    
    # 数据备份和导出配置
    data_backup_path: str = Field(default="backups", description="备份文件存储路径")
    backup_retention_days: int = Field(default=30, description="备份保留天数")
    export_temp_path: str = Field(default="exports/temp", description="导出临时文件路径")
    max_export_size: int = Field(default=500 * 1024 * 1024, description="最大导出文件大小(500MB)")
    
    # Celery任务队列配置
    celery_broker_url: str = Field(default="redis://localhost:6379/1", description="Celery消息代理URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/1", description="Celery结果后端URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def ai_config(self):
        """获取AI服务配置"""
        # 动态导入以避免循环依赖
        from app.services.ai.base import AIProvider, AIConfig
        
        return AIConfig(
            stt_provider=AIProvider.OPENAI,
            llm_provider=AIProvider.OPENAI,
            stt_config={
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.whisper_model,
                "timeout": 60,
                "http_proxy": self.http_proxy,
                "https_proxy": self.https_proxy,
                "proxy_auth": self.proxy_auth
            },
            llm_config={
                "api_key": self.openai_api_key,
                "base_url": self.openai_base_url,
                "model": self.openai_model,
                "timeout": 60,
                "http_proxy": self.http_proxy,
                "https_proxy": self.https_proxy,
                "proxy_auth": self.proxy_auth
            },
            default_stt_model=self.whisper_model,
            default_llm_model=self.openai_model
        )
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        Path(self.upload_dir).mkdir(exist_ok=True)
        Path(self.upload_dir, "audio").mkdir(exist_ok=True)
        Path(self.upload_dir, "temp").mkdir(exist_ok=True)
        Path(self.data_backup_path).mkdir(exist_ok=True)
        Path(self.export_temp_path).mkdir(parents=True, exist_ok=True)


# 创建全局配置实例
settings = Settings()
settings.ensure_directories()