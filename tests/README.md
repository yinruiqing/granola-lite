# Granola 测试套件

本目录包含 Granola 项目的所有测试文件。

## 测试文件说明

### `test_integration.py`
前后端集成测试脚本，包括：
- 后端API端点测试
- 前端页面访问测试
- CORS配置测试
- API合约兼容性测试
- 错误处理测试

### `final_test.py`
综合联调测试脚本，包括：
- 完整的健康检查
- API功能测试
- CORS和安全测试
- 错误处理测试
- 性能测试
- 详细的测试报告

### `test_proxy_config.py`
代理配置测试脚本，包括：
- 代理配置加载测试
- OpenAI服务代理集成测试
- 代理认证功能测试
- 各种代理场景覆盖

## 如何运行测试

### 前提条件
确保前后端服务都在运行：
- 后端服务: `python -m uvicorn api_main:app --reload --port 8000`
- 前端服务: `cd frontend && npm run dev`

### 运行集成测试
```bash
# 基础集成测试
python tests/test_integration.py

# 综合联调测试
python tests/final_test.py

# 代理配置测试
python tests/test_proxy_config.py
```

### 测试结果
- 所有测试通过时返回退出码 0
- 测试失败时返回退出码 1
- 详细的测试结果会显示在控制台

## 测试覆盖范围

- ✅ 后端API健康检查
- ✅ 前端页面访问
- ✅ 模板管理API
- ✅ 会议管理API  
- ✅ 笔记管理API
- ✅ CORS跨域配置
- ✅ 错误处理机制
- ✅ 基础性能测试

## 开发说明

添加新测试时请确保：
1. 遵循现有的测试结构和命名规范
2. 添加适当的错误处理和断言
3. 更新本README文档