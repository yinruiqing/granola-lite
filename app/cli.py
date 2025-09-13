"""
命令行接口 - 统一的启动和管理命令
"""

import asyncio
import click
import uvicorn
from pathlib import Path
from typing import Optional

from app.config import settings
from app.core.logging import setup_logging, api_logger


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Granola Lite - AI会议记录助手"""
    pass


@main.command()
@click.option('--host', default=None, help='服务器地址')
@click.option('--port', default=None, type=int, help='服务器端口')
@click.option('--reload', is_flag=True, help='开启自动重载')
@click.option('--workers', default=1, type=int, help='工作进程数')
@click.option('--log-level', default='info', 
              type=click.Choice(['debug', 'info', 'warning', 'error', 'critical']),
              help='日志级别')
def server(host: Optional[str], port: Optional[int], reload: bool, 
           workers: int, log_level: str):
    """启动API服务器"""
    host = host or settings.host
    port = port or settings.port
    
    setup_logging(level=log_level.upper())
    api_logger.info(f"启动服务器: {host}:{port}")
    
    if reload and workers > 1:
        api_logger.warning("重载模式不支持多进程，将使用单进程")
        workers = 1
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        log_level=log_level,
        access_log=True
    )


@main.command()
@click.option('--upgrade', is_flag=True, help='升级数据库到最新版本')
@click.option('--revision', default=None, help='迁移到指定版本')
@click.option('--sql', is_flag=True, help='只显示SQL而不执行')
@click.option('--create', is_flag=True, help='创建新的迁移')
@click.option('--message', default=None, help='迁移消息')
def db(upgrade: bool, revision: Optional[str], sql: bool, create: bool, message: Optional[str]):
    """数据库迁移命令"""
    import subprocess
    import sys
    
    if create:
        if not message:
            message = click.prompt('迁移消息')
        cmd = ['alembic', 'revision', '--autogenerate', '-m', message]
        api_logger.info(f"创建新迁移: {message}")
    elif upgrade:
        cmd = ['alembic', 'upgrade', revision or 'head']
        if sql:
            cmd.append('--sql')
        api_logger.info(f"升级数据库到: {revision or 'head'}")
    else:
        cmd = ['alembic', 'current']
        api_logger.info("显示当前数据库版本")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        click.echo(result.stdout)
    if result.stderr:
        click.echo(result.stderr, err=True)
    
    if result.returncode != 0:
        sys.exit(result.returncode)


@main.command()
@click.option('--workers', default=4, type=int, help='Celery工作进程数')
@click.option('--loglevel', default='info', 
              type=click.Choice(['debug', 'info', 'warning', 'error']),
              help='日志级别')
@click.option('--queue', default='default', help='处理的队列名称')
def worker(workers: int, loglevel: str, queue: str):
    """启动Celery后台任务处理器"""
    from app.core.celery_app import celery_app
    
    api_logger.info(f"启动Celery工作进程: {workers} 个")
    
    celery_app.worker_main([
        'worker',
        '--loglevel', loglevel,
        '--concurrency', str(workers),
        '--queues', queue
    ])


@main.command()
def beat():
    """启动Celery定时任务调度器"""
    from app.core.celery_app import celery_app
    
    api_logger.info("启动Celery定时任务调度器")
    
    celery_app.worker_main([
        'beat',
        '--loglevel', 'info'
    ])


@main.command()
@click.option('--format', default='json', type=click.Choice(['json', 'markdown']),
              help='导出格式')
@click.option('--output', default=None, help='输出文件路径')
def export-api-docs(format: str, output: Optional[str]):
    """导出API文档"""
    from app.main import app
    
    if format == 'json':
        import json
        openapi_schema = app.openapi()
        content = json.dumps(openapi_schema, indent=2, ensure_ascii=False)
        default_filename = 'api-docs.json'
    else:
        # 生成Markdown格式的API文档
        content = generate_markdown_docs()
        default_filename = 'api-docs.md'
    
    output_file = output or default_filename
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    api_logger.info(f"API文档已导出到: {output_file}")


@main.command()
@click.option('--check', is_flag=True, help='只检查健康状态')
def health(check: bool):
    """健康检查"""
    async def run_health_check():
        from app.core.health import health_checker
        result = await health_checker.full_health_check()
        
        status_emoji = {
            'healthy': '✅',
            'warning': '⚠️',
            'unhealthy': '❌',
            'critical': '🔴'
        }
        
        click.echo(f"{status_emoji.get(result['status'], '❓')} 系统状态: {result['status']}")
        
        for service, info in result['services'].items():
            service_status = status_emoji.get(info['status'], '❓')
            click.echo(f"  {service_status} {service}: {info['status']}")
            if info.get('message'):
                click.echo(f"      {info['message']}")
        
        return result['status'] == 'healthy' or result['status'] == 'warning'
    
    if check:
        healthy = asyncio.run(run_health_check())
        exit(0 if healthy else 1)


@main.command()
@click.option('--env', default='.env', help='环境变量文件路径')
def init(env: str):
    """初始化项目"""
    from app.db.init_db import init_database
    
    api_logger.info("初始化Granola项目...")
    
    # 创建环境变量文件
    env_path = Path(env)
    if not env_path.exists():
        env_content = f"""# Granola Lite Configuration
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./granola.db
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/granola

# AI Services
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
WHISPER_MODEL=whisper-1

# Security
SECRET_KEY={settings.secret_key}
ALGORITHM=HS256

# File Storage
UPLOAD_DIR=uploads
MAX_FILE_SIZE=104857600

# Redis (optional)
# REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
"""
        env_path.write_text(env_content)
        api_logger.info(f"已创建环境配置文件: {env_path}")
    
    # 创建必要目录
    settings.ensure_directories()
    api_logger.info("已创建必要目录")
    
    # 初始化数据库
    asyncio.run(init_database())
    api_logger.info("数据库初始化完成")
    
    api_logger.info("✅ 项目初始化完成!")
    api_logger.info("下一步:")
    api_logger.info("1. 编辑 .env 文件配置你的API密钥")
    api_logger.info("2. 运行 'granola-server server' 启动服务")


def generate_markdown_docs() -> str:
    """生成Markdown格式的API文档"""
    from app.main import app
    
    openapi_schema = app.openapi()
    
    md_content = f"""# {openapi_schema['info']['title']}

Version: {openapi_schema['info']['version']}
Description: {openapi_schema['info'].get('description', '')}

## Base URL

```
{settings.host}:{settings.port}
```

## Endpoints

"""
    
    for path, methods in openapi_schema['paths'].items():
        md_content += f"\n### {path}\n\n"
        
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'delete', 'patch']:
                summary = details.get('summary', '')
                description = details.get('description', '')
                
                md_content += f"#### {method.upper()} {path}\n\n"
                if summary:
                    md_content += f"**Summary:** {summary}\n\n"
                if description:
                    md_content += f"**Description:** {description}\n\n"
                
                # Parameters
                if 'parameters' in details:
                    md_content += "**Parameters:**\n\n"
                    for param in details['parameters']:
                        param_type = param.get('schema', {}).get('type', 'unknown')
                        required = '(required)' if param.get('required') else '(optional)'
                        md_content += f"- `{param['name']}` ({param_type}) {required}: {param.get('description', '')}\n"
                    md_content += "\n"
                
                md_content += "---\n\n"
    
    return md_content


if __name__ == '__main__':
    main()