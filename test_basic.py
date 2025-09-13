#!/usr/bin/env python3
"""
基础测试脚本 - 测试API基本功能
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_basic_endpoints():
    """测试基础端点"""
    
    print("🧪 测试基础API端点...")
    
    # 测试根路径
    print("\n1. 测试根路径 GET /")
    response = requests.get(f"{BASE_URL}/")
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
    assert response.status_code == 200
    
    # 测试健康检查
    print("\n2. 测试健康检查 GET /health") 
    response = requests.get(f"{BASE_URL}/health")
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
    assert response.status_code == 200
    
    # 测试OpenAPI文档
    print("\n3. 测试OpenAPI规范 GET /openapi.json")
    response = requests.get(f"{BASE_URL}/openapi.json")
    print(f"   状态码: {response.status_code}")
    openapi_data = response.json()
    print(f"   API标题: {openapi_data['info']['title']}")
    print(f"   API版本: {openapi_data['info']['version']}")
    assert response.status_code == 200
    
    # 测试文档页面
    print("\n4. 测试文档页面 GET /docs")
    response = requests.get(f"{BASE_URL}/docs")
    print(f"   状态码: {response.status_code}")
    print(f"   内容类型: {response.headers.get('content-type')}")
    assert response.status_code == 200
    assert "text/html" in response.headers.get('content-type', '')
    
    print("\n✅ 所有基础端点测试通过！")


def test_error_handling():
    """测试错误处理"""
    
    print("\n🧪 测试错误处理...")
    
    # 测试404错误
    print("\n1. 测试404错误")
    response = requests.get(f"{BASE_URL}/nonexistent")
    print(f"   状态码: {response.status_code}")
    assert response.status_code == 404
    
    # 测试方法不允许
    print("\n2. 测试方法不允许")
    response = requests.post(f"{BASE_URL}/health")
    print(f"   状态码: {response.status_code}")
    assert response.status_code == 405
    
    print("\n✅ 错误处理测试通过！")


def main():
    """主测试函数"""
    
    print("🚀 开始Granola API基础功能测试\n")
    
    try:
        test_basic_endpoints()
        test_error_handling()
        
        print("\n🎉 所有测试通过! 后端API基础功能正常")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)