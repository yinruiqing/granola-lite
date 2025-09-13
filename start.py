#!/usr/bin/env python3
"""
Granola API 启动脚本
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def main():
    """主启动函数"""
    # 检查环境变量文件
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  未找到 .env 文件，正在创建...")
        example_env = project_root / ".env.example"
        if example_env.exists():
            import shutil
            shutil.copy(example_env, env_file)
            print("✅ 已创建 .env 文件，请配置必要的环境变量")
        else:
            print("❌ 未找到 .env.example 文件")
            sys.exit(1)
    
    # 检查必要的目录
    directories = ["uploads", "uploads/audio", "uploads/temp", "logs"]
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(exist_ok=True)
    
    print("🚀 启动 Granola API...")
    
    # 导入配置
    try:
        from app.config import settings
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        print("请检查 .env 文件中的配置项")
        sys.exit(1)
    
    # 检查必要配置
    if not settings.openai_api_key:
        print("❌ 请在 .env 文件中配置 OPENAI_API_KEY")
        sys.exit(1)
    
    print(f"📊 运行模式: {'开发' if settings.debug else '生产'}")
    print(f"🌐 服务地址: http://{settings.host}:{settings.port}")
    print(f"📖 API文档: http://{settings.host}:{settings.port}/docs")
    
    # 启动服务
    import uvicorn
    
    config = uvicorn.Config(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        reload_dirs=[str(project_root / "app")] if settings.debug else None,
        log_level="info" if not settings.debug else "debug",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Granola API 已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)