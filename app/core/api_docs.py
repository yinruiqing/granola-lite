"""
API文档和OpenAPI增强系统
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse
import json
from pathlib import Path

from app.config import settings


class APIDocumentation:
    """API文档管理器"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.custom_openapi_schema = None
    
    def enhance_openapi_schema(self) -> Dict[str, Any]:
        """增强OpenAPI架构"""
        if self.custom_openapi_schema:
            return self.custom_openapi_schema
        
        openapi_schema = get_openapi(
            title=settings.app_name,
            version=settings.app_version,
            description=self._get_api_description(),
            routes=self.app.routes,
            servers=self._get_servers_info(),
        )
        
        # 添加自定义信息
        openapi_schema["info"].update({
            "contact": {
                "name": "Granola API Support",
                "url": "https://github.com/granola/support",
                "email": "support@granola.com"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            },
            "termsOfService": "https://granola.com/terms"
        })
        
        # 添加安全定义
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT认证令牌"
            }
        }
        
        # 添加全局安全要求
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        # 添加标签描述
        openapi_schema["tags"] = self._get_api_tags()
        
        # 添加示例
        self._add_examples_to_schema(openapi_schema)
        
        # 添加响应模板
        self._add_response_templates(openapi_schema)
        
        self.custom_openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_api_description(self) -> str:
        """获取API描述"""
        return """
# Granola Meeting Notes API

Granola是一个AI驱动的会议笔记和转录系统，提供以下核心功能：

## 🎯 核心功能
- **音频转录**: 使用最新的AI技术将音频转换为文本
- **智能笔记**: AI增强的会议笔记生成和优化
- **实时协作**: WebSocket支持的实时转录和协作
- **多语言支持**: 支持多种语言的转录和处理
- **文件管理**: 完整的文件上传、存储和管理系统

## 🔧 技术特性
- **高性能**: 异步处理和缓存优化
- **可扩展**: 微服务架构和插件化设计
- **安全**: JWT认证和权限控制
- **监控**: 完整的监控和日志系统
- **任务队列**: Celery驱动的异步任务处理

## 🚀 开始使用
1. 获取API密钥
2. 进行身份认证
3. 上传音频文件
4. 获取转录结果
5. 创建和管理笔记

## 📋 API版本
当前版本: v1.0.0  
文档更新: 实时更新  
状态: 生产就绪

---
*有问题？查看我们的 [支持文档](https://docs.granola.com) 或 [联系我们](mailto:support@granola.com)*
        """
    
    def _get_servers_info(self) -> List[Dict[str, str]]:
        """获取服务器信息"""
        return [
            {
                "url": "https://api.granola.com/api/v1",
                "description": "生产环境"
            },
            {
                "url": "https://staging-api.granola.com/api/v1",
                "description": "测试环境"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "本地开发环境"
            }
        ]
    
    def _get_api_tags(self) -> List[Dict[str, str]]:
        """获取API标签"""
        return [
            {
                "name": "authentication",
                "description": "🔐 用户认证和授权管理"
            },
            {
                "name": "audio",
                "description": "🎵 音频文件上传和管理"
            },
            {
                "name": "transcriptions",
                "description": "📝 语音转录服务"
            },
            {
                "name": "notes",
                "description": "📋 笔记创建和管理"
            },
            {
                "name": "ai-enhancement",
                "description": "🤖 AI驱动的内容增强"
            },
            {
                "name": "meetings",
                "description": "🏢 会议管理和组织"
            },
            {
                "name": "websocket",
                "description": "⚡ 实时通信和协作"
            },
            {
                "name": "file-storage",
                "description": "💾 文件存储和管理"
            },
            {
                "name": "ai-service",
                "description": "🧠 AI服务管理"
            },
            {
                "name": "cache",
                "description": "⚡ 缓存管理"
            },
            {
                "name": "task-queue",
                "description": "⏳ 异步任务管理"
            },
            {
                "name": "monitoring",
                "description": "📊 系统监控和指标"
            },
            {
                "name": "data-management",
                "description": "💾 数据导入导出和迁移"
            },
            {
                "name": "performance",
                "description": "⚡ 性能优化和监控"
            },
            {
                "name": "security",
                "description": "🔒 安全管理和防护"
            }
        ]
    
    def _add_examples_to_schema(self, schema: Dict[str, Any]):
        """添加示例到架构"""
        # 为常用端点添加请求和响应示例
        examples = {
            "/auth/login": {
                "requestBody": {
                    "content": {
                        "application/json": {
                            "example": {
                                "email": "user@example.com",
                                "password": "secure_password"
                            }
                        }
                    }
                }
            },
            "/transcriptions": {
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "transcription": {
                                        "id": 123,
                                        "text": "这是转录的内容...",
                                        "language": "zh",
                                        "confidence": 0.95,
                                        "duration": 120.5,
                                        "created_at": "2024-01-01T12:00:00Z"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # 将示例应用到架构
        for path, path_examples in examples.items():
            if path in schema.get("paths", {}):
                for method in schema["paths"][path]:
                    if isinstance(schema["paths"][path][method], dict):
                        for example_type, example_data in path_examples.items():
                            if example_type in schema["paths"][path][method]:
                                schema["paths"][path][method][example_type].update(example_data)
    
    def _add_response_templates(self, schema: Dict[str, Any]):
        """添加响应模板"""
        # 定义通用响应模板
        common_responses = {
            "400": {
                "description": "请求参数错误",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string", "example": "Invalid request parameters"},
                                "detail": {"type": "string", "example": "The email field is required"}
                            }
                        }
                    }
                }
            },
            "401": {
                "description": "未授权访问",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string", "example": "Unauthorized"},
                                "detail": {"type": "string", "example": "Invalid or expired token"}
                            }
                        }
                    }
                }
            },
            "403": {
                "description": "权限不足",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string", "example": "Forbidden"},
                                "detail": {"type": "string", "example": "Insufficient permissions"}
                            }
                        }
                    }
                }
            },
            "404": {
                "description": "资源未找到",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string", "example": "Not Found"},
                                "detail": {"type": "string", "example": "The requested resource was not found"}
                            }
                        }
                    }
                }
            },
            "500": {
                "description": "服务器内部错误",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean", "example": False},
                                "error": {"type": "string", "example": "Internal Server Error"},
                                "detail": {"type": "string", "example": "An unexpected error occurred"}
                            }
                        }
                    }
                }
            }
        }
        
        # 将通用响应添加到组件中
        if "components" not in schema:
            schema["components"] = {}
        
        if "responses" not in schema["components"]:
            schema["components"]["responses"] = {}
        
        schema["components"]["responses"].update(common_responses)
    
    def generate_custom_docs_html(self, openapi_url: str) -> str:
        """生成自定义文档HTML"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{settings.app_name} - API文档</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui.css" />
    <style>
        .topbar {{ display: none; }}
        .swagger-ui .info .title {{ color: #2c3e50; }}
        .swagger-ui .info {{ margin: 20px 0; }}
        .swagger-ui .scheme-container {{ 
            background: #f8f9fa; 
            border: 1px solid #dee2e6; 
            border-radius: 8px; 
            padding: 15px;
            margin: 20px 0;
        }}
        .custom-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
        }}
        .custom-header h1 {{
            margin: 0;
            font-size: 2rem;
        }}
        .custom-header p {{
            margin: 5px 0 0 0;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@3.25.0/swagger-ui-bundle.js"></script>
    <script>
        const ui = SwaggerUIBundle({{
            url: '{openapi_url}',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            plugins: [
                SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            requestInterceptor: function(request) {{
                // 可以在这里添加全局请求拦截逻辑
                return request;
            }},
            responseInterceptor: function(response) {{
                // 可以在这里添加全局响应拦截逻辑
                return response;
            }},
            onComplete: function() {{
                // 文档加载完成后的回调
                console.log('API文档加载完成');
            }}
        }});
        
        // 添加自定义头部
        document.addEventListener('DOMContentLoaded', function() {{
            const header = document.createElement('div');
            header.className = 'custom-header';
            header.innerHTML = `
                <h1>🍯 {settings.app_name} API</h1>
                <p>版本 {settings.app_version} | 智能会议笔记和转录系统</p>
            `;
            
            const swaggerUI = document.getElementById('swagger-ui');
            swaggerUI.insertBefore(header, swaggerUI.firstChild);
        }});
    </script>
</body>
</html>
        """
    
    def generate_redoc_html(self, openapi_url: str) -> str:
        """生成ReDoc HTML"""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{settings.app_name} - API文档 (ReDoc)</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body {{ margin: 0; padding: 0; }}
        .custom-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            margin-bottom: 0;
        }}
        .custom-header h1 {{
            margin: 0;
            font-size: 2.5rem;
            font-weight: 300;
        }}
        .custom-header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1rem;
        }}
    </style>
    <redoc spec-url='{openapi_url}' theme='{{
        "colors": {{
            "primary": {{
                "main": "#667eea"
            }}
        }},
        "typography": {{
            "fontSize": "14px",
            "lineHeight": "1.5em",
            "code": {{
                "fontSize": "13px",
                "fontFamily": "Courier, monospace"
            }},
            "headings": {{
                "fontFamily": "Montserrat, sans-serif",
                "fontWeight": "400"
            }}
        }}
    }}'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const header = document.createElement('div');
            header.className = 'custom-header';
            header.innerHTML = `
                <h1>🍯 {settings.app_name} API</h1>
                <p>版本 {settings.app_version} | 详细的API文档和示例</p>
            `;
            
            document.body.insertBefore(header, document.body.firstChild);
        }});
    </script>
</head>
<body>
</body>
</html>
        """
    
    def export_openapi_spec(self, file_path: str = None) -> str:
        """导出OpenAPI规范"""
        if not file_path:
            file_path = "openapi.json"
        
        schema = self.enhance_openapi_schema()
        
        # 确保目录存在
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        
        return file_path
    
    def generate_postman_collection(self) -> Dict[str, Any]:
        """生成Postman集合"""
        schema = self.enhance_openapi_schema()
        
        collection = {
            "info": {
                "name": f"{settings.app_name} API",
                "description": schema["info"]["description"],
                "version": schema["info"]["version"],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "{{base_url}}",
                    "type": "string"
                },
                {
                    "key": "access_token",
                    "value": "your_jwt_token_here",
                    "type": "string"
                }
            ],
            "item": []
        }
        
        # 转换路径到Postman项目
        for path, methods in schema.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    item = {
                        "name": details.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json",
                                    "type": "text"
                                }
                            ],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.strip('/').split('/')
                            }
                        },
                        "response": []
                    }
                    
                    # 添加描述
                    if "description" in details:
                        item["request"]["description"] = details["description"]
                    
                    collection["item"].append(item)
        
        return collection


# 全局API文档实例（在应用初始化时设置）
api_documentation: Optional[APIDocumentation] = None


def setup_api_documentation(app: FastAPI) -> APIDocumentation:
    """设置API文档"""
    global api_documentation
    api_documentation = APIDocumentation(app)
    
    # 设置自定义OpenAPI架构生成器
    def custom_openapi():
        return api_documentation.enhance_openapi_schema()
    
    app.openapi = custom_openapi
    
    return api_documentation


__all__ = [
    'APIDocumentation',
    'api_documentation',
    'setup_api_documentation'
]