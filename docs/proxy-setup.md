# OpenAI API 代理配置指南

本文档介绍如何为 Granola 项目配置 OpenAI API 代理，以便在需要通过代理服务器访问 OpenAI 服务的环境中使用。

## 配置方法

### 1. 环境变量配置

在 `.env` 文件中添加以下代理配置：

```bash
# HTTP代理配置
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080

# 如果代理需要认证
PROXY_AUTH=username:password
```

### 2. 支持的代理类型

#### HTTP代理
```bash
HTTP_PROXY=http://proxy.example.com:8080
```

#### HTTPS代理
```bash
HTTPS_PROXY=https://proxy.example.com:8080
```

#### SOCKS代理
```bash
HTTP_PROXY=socks5://proxy.example.com:1080
HTTPS_PROXY=socks5://proxy.example.com:1080
```

### 3. 代理认证

如果您的代理服务器需要用户名和密码认证：

```bash
PROXY_AUTH=your_username:your_password
```

## 配置示例

### 基本HTTP代理
```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
HTTP_PROXY=http://192.168.1.100:8080
HTTPS_PROXY=http://192.168.1.100:8080
```

### 带认证的代理
```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
HTTP_PROXY=http://proxy.company.com:8080
HTTPS_PROXY=http://proxy.company.com:8080
PROXY_AUTH=employee:password123
```

### 使用SOCKS代理
```bash
# .env 文件
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
HTTP_PROXY=socks5://127.0.0.1:1080
HTTPS_PROXY=socks5://127.0.0.1:1080
```

## 验证配置

### 1. 启动服务
```bash
python -m uvicorn api_main:app --reload --port 8000
```

### 2. 测试API连接
```bash
# 测试模板API（会调用OpenAI）
curl http://localhost:8000/api/v1/templates
```

### 3. 查看日志
检查服务启动日志，确认代理配置正确加载：
```
INFO: Proxy configuration loaded
INFO: HTTP Proxy: http://proxy.example.com:8080
INFO: HTTPS Proxy: http://proxy.example.com:8080
```

## 故障排除

### 常见问题

#### 1. 代理连接超时
**症状**: OpenAI API调用超时
**解决**: 检查代理服务器地址和端口是否正确

#### 2. 代理认证失败
**症状**: 401 Unauthorized 错误
**解决**: 验证用户名和密码是否正确，格式为 `username:password`

#### 3. SSL证书错误
**症状**: SSL verification failed
**解决**: 如果使用自签名证书的代理，可能需要配置证书验证

### 调试步骤

1. **检查代理连通性**:
   ```bash
   curl --proxy http://proxy.example.com:8080 https://api.openai.com/v1/models
   ```

2. **验证认证信息**:
   ```bash
   curl --proxy http://username:password@proxy.example.com:8080 https://api.openai.com/v1/models
   ```

3. **查看详细日志**:
   设置环境变量 `DEBUG=true` 启用详细日志

## 安全注意事项

1. **保护认证信息**: 不要在代码中硬编码代理认证信息
2. **使用环境变量**: 将敏感信息存储在 `.env` 文件中
3. **文件权限**: 确保 `.env` 文件具有适当的访问权限 (600)
4. **版本控制**: 不要将 `.env` 文件提交到版本控制系统

## 性能优化

### 连接池配置
代理配置会自动使用 httpx 的连接池功能，以提高性能：

- 复用连接
- 自动重试
- 超时控制
- 并发限制

### 超时设置
可以通过环境变量调整超时时间：
```bash
OPENAI_TIMEOUT=120  # 2分钟超时
```

## 支持的代理服务器

本配置支持以下类型的代理服务器：
- Squid
- Nginx (proxy mode)
- Apache (mod_proxy)
- HAProxy
- Shadowsocks
- V2Ray
- 其他标准HTTP/HTTPS/SOCKS代理

如有问题，请查看项目文档或提交 Issue。