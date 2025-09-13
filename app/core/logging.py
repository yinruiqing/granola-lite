"""
日志配置
"""

import sys
import logging
from pathlib import Path
from loguru import logger
from typing import Dict, Any

# settings将在需要时动态导入以避免循环依赖


class InterceptHandler(logging.Handler):
    """拦截标准库日志并转发给loguru"""
    
    def emit(self, record):
        # 获取对应的loguru等级
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 查找调用者
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """设置应用日志"""
    
    # 动态导入settings以避免循环依赖
    try:
        from app.config import settings
        debug_mode = settings.debug
    except:
        debug_mode = False
    
    # 移除默认的loguru处理器
    logger.remove()
    
    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 控制台日志
    logger.add(
        sys.stdout,
        format=log_format,
        level="DEBUG" if debug_mode else "INFO",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 文件日志
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 应用日志
    logger.add(
        log_dir / "granola.log",
        format=log_format,
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # 错误日志
    logger.add(
        log_dir / "granola_error.log",
        format=log_format,
        level="ERROR",
        rotation="1 week",
        retention="90 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # AI服务日志
    logger.add(
        log_dir / "ai_service.log",
        format=log_format,
        level="INFO",
        rotation="1 day",
        retention="7 days",
        filter=lambda record: "ai_service" in record["name"].lower(),
        backtrace=True,
        diagnose=True
    )
    
    # 拦截标准库日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # 设置第三方库日志级别
    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        
    # 设置SQLAlchemy日志级别
    if not settings.debug:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str):
    """获取特定名称的日志器"""
    return logger.bind(name=name)


# 创建模块专用日志器
api_logger = get_logger("api")
service_logger = get_logger("service")
ai_logger = get_logger("ai_service")
db_logger = get_logger("database")
audio_logger = get_logger("audio_processing")