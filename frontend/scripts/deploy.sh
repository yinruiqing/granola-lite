#!/bin/bash

# Granola Lite 部署脚本

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 函数：打印彩色消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 函数：检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查必要工具
print_message $BLUE "🔍 检查部署环境..."

if ! command_exists node; then
    print_message $RED "❌ Node.js 未安装"
    exit 1
fi

if ! command_exists npm; then
    print_message $RED "❌ npm 未安装"
    exit 1
fi

print_message $GREEN "✅ 环境检查通过"

# 获取参数
ENVIRONMENT=${1:-development}
SKIP_TESTS=${2:-false}

print_message $BLUE "📋 部署配置:"
echo "  环境: $ENVIRONMENT"
echo "  跳过测试: $SKIP_TESTS"

# 安装依赖
print_message $BLUE "📦 安装依赖..."
npm ci

# 运行测试 (可选)
if [ "$SKIP_TESTS" != "true" ]; then
    print_message $BLUE "🧪 运行测试..."
    npm run test:ci
    
    print_message $BLUE "🔍 运行代码检查..."
    npm run lint
    
    print_message $GREEN "✅ 所有测试通过"
else
    print_message $YELLOW "⚠️  跳过测试阶段"
fi

# 构建应用
print_message $BLUE "🏗️  构建应用..."
if [ "$ENVIRONMENT" = "production" ]; then
    NODE_ENV=production npm run build
else
    npm run build
fi

# 分析构建结果
print_message $BLUE "📊 分析构建结果..."
node scripts/analyze-bundle.js

# 运行安全检查 (如果工具可用)
if command_exists npm-audit; then
    print_message $BLUE "🔒 运行安全检查..."
    npm audit --audit-level moderate
fi

# 部署到不同环境
case $ENVIRONMENT in
    "production")
        print_message $BLUE "🚀 部署到生产环境..."
        
        # 这里可以添加具体的生产环境部署逻辑
        # 例如：部署到 Vercel, Netlify, 或自定义服务器
        
        if command_exists vercel; then
            vercel --prod
        else
            print_message $YELLOW "⚠️  Vercel CLI 未安装，跳过部署"
        fi
        ;;
        
    "staging")
        print_message $BLUE "🚀 部署到测试环境..."
        
        if command_exists vercel; then
            vercel
        else
            print_message $YELLOW "⚠️  Vercel CLI 未安装，跳过部署"
        fi
        ;;
        
    "development")
        print_message $BLUE "🚀 启动开发服务器..."
        npm run dev
        ;;
        
    *)
        print_message $RED "❌ 未知环境: $ENVIRONMENT"
        print_message $YELLOW "支持的环境: production, staging, development"
        exit 1
        ;;
esac

print_message $GREEN "🎉 部署完成!"

# 显示部署后的建议
print_message $BLUE "💡 部署后检查清单:"
echo "  □ 检查应用是否正常启动"
echo "  □ 验证核心功能是否正常工作"
echo "  □ 检查性能指标"
echo "  □ 验证PWA功能"
echo "  □ 测试离线功能"

# 如果是生产环境，显示额外提醒
if [ "$ENVIRONMENT" = "production" ]; then
    print_message $YELLOW "⚠️  生产环境部署提醒:"
    echo "  • 确保备份了重要数据"
    echo "  • 监控应用性能和错误率"
    echo "  • 准备回滚计划"
fi