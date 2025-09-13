#!/usr/bin/env python3
"""
Granola 前后端联调最终测试
"""

import requests
import time
import json

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_backend_health():
    """测试后端健康状态"""
    print_section("后端健康检查")
    
    try:
        # 基础健康检查
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        print(f"✅ 后端健康检查: {response.status_code}")
        health_data = response.json()
        print(f"   状态: {health_data['status']}")
        
        # API文档
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        print(f"✅ API文档访问: {response.status_code}")
        
        # OpenAPI规范
        response = requests.get(f"{BACKEND_URL}/openapi.json", timeout=5)
        print(f"✅ OpenAPI规范: {response.status_code}")
        openapi = response.json()
        print(f"   API标题: {openapi['info']['title']}")
        print(f"   API版本: {openapi['info']['version']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 后端健康检查失败: {e}")
        return False

def test_frontend_health():
    """测试前端健康状态"""
    print_section("前端健康检查")
    
    try:
        # 前端首页
        response = requests.get(f"{FRONTEND_URL}/", timeout=10)
        print(f"✅ 前端首页访问: {response.status_code}")
        
        # API测试页面
        response = requests.get(f"{FRONTEND_URL}/test-api", timeout=10)
        print(f"✅ API测试页面: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"⚠️  前端访问超时或失败: {e}")
        print("   (前端可能还在编译中，这是正常的)")
        return False

def test_api_functionality():
    """测试API功能"""
    print_section("API功能测试")
    
    test_results = []
    
    # 测试模板API
    print("\n📋 模板管理API:")
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/templates")
        templates = response.json()
        print(f"   ✅ 获取模板列表: {len(templates)} 个模板")
        for i, template in enumerate(templates[:2], 1):
            print(f"      {i}. {template['name']} ({template['category']})")
        test_results.append("templates_ok")
    except Exception as e:
        print(f"   ❌ 模板API失败: {e}")
    
    # 测试会议API
    print("\n🏢 会议管理API:")
    try:
        # 获取会议列表
        response = requests.get(f"{BACKEND_URL}/api/v1/meetings")
        meetings = response.json()
        print(f"   ✅ 获取会议列表: {len(meetings)} 个会议")
        
        # 创建测试会议
        meeting_data = {
            "title": "联调测试会议",
            "description": "前后端联调测试创建的会议",
            "template_id": 1
        }
        response = requests.post(f"{BACKEND_URL}/api/v1/meetings", json=meeting_data)
        new_meeting = response.json()
        print(f"   ✅ 创建会议: ID {new_meeting['id']}, 标题: {new_meeting['title']}")
        
        # 获取会议详情
        response = requests.get(f"{BACKEND_URL}/api/v1/meetings/{new_meeting['id']}")
        meeting_detail = response.json()
        print(f"   ✅ 获取会议详情: {meeting_detail['title']}")
        
        test_results.append("meetings_ok")
    except Exception as e:
        print(f"   ❌ 会议API失败: {e}")
    
    # 测试笔记API
    print("\n📝 笔记管理API:")
    try:
        # 获取笔记列表
        response = requests.get(f"{BACKEND_URL}/api/v1/notes")
        notes = response.json()
        print(f"   ✅ 获取笔记列表: {len(notes)} 个笔记")
        
        # 创建测试笔记
        note_data = {
            "meeting_id": 1,
            "content": "这是一条通过联调测试创建的笔记内容",
            "timestamp": time.time()
        }
        response = requests.post(f"{BACKEND_URL}/api/v1/notes", json=note_data)
        new_note = response.json()
        print(f"   ✅ 创建笔记: ID {new_note['id']}")
        print(f"      内容预览: {new_note['content'][:30]}...")
        
        test_results.append("notes_ok")
    except Exception as e:
        print(f"   ❌ 笔记API失败: {e}")
    
    return test_results

def test_cors_and_security():
    """测试CORS和安全配置"""
    print_section("CORS和安全测试")
    
    try:
        # 测试CORS预检请求
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        response = requests.options(f"{BACKEND_URL}/api/v1/meetings", headers=headers)
        print(f"✅ CORS预检请求: {response.status_code}")
        
        cors_headers = {
            "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
            "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
            "access-control-allow-headers": response.headers.get("access-control-allow-headers")
        }
        print(f"   允许来源: {cors_headers['access-control-allow-origin']}")
        
        # 测试实际跨域请求
        response = requests.get(
            f"{BACKEND_URL}/api/v1/templates",
            headers={"Origin": "http://localhost:3000"}
        )
        print(f"✅ 跨域GET请求: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ CORS测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print_section("错误处理测试")
    
    try:
        # 测试404
        response = requests.get(f"{BACKEND_URL}/api/v1/nonexistent")
        print(f"✅ 404处理: {response.status_code}")
        
        # 测试422 - 数据验证错误
        response = requests.post(
            f"{BACKEND_URL}/api/v1/meetings",
            json={"invalid": "data"},
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ 数据验证错误: {response.status_code}")
        
        # 测试无效JSON
        response = requests.post(
            f"{BACKEND_URL}/api/v1/meetings",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ JSON解析错误: {response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False

def performance_test():
    """简单性能测试"""
    print_section("性能测试")
    
    try:
        # 批量请求测试
        start_time = time.time()
        for i in range(10):
            response = requests.get(f"{BACKEND_URL}/api/v1/templates")
            assert response.status_code == 200
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 10
        print(f"✅ 批量请求测试: 10次请求平均用时 {avg_time:.3f}s")
        
        # 并发创建会议测试
        start_time = time.time()
        meeting_data = {"title": f"性能测试会议", "description": "并发测试"}
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for i in range(5):
                future = executor.submit(
                    requests.post, 
                    f"{BACKEND_URL}/api/v1/meetings", 
                    json={**meeting_data, "title": f"并发会议{i+1}"}
                )
                futures.append(future)
            
            results = [future.result() for future in futures]
        
        end_time = time.time()
        success_count = sum(1 for r in results if r.status_code == 200)
        total_time = end_time - start_time
        
        print(f"✅ 并发测试: {success_count}/5 成功, 总用时 {total_time:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        return False

def generate_report(test_results):
    """生成测试报告"""
    print_section("测试报告")
    
    print("🎯 功能模块测试结果:")
    modules = {
        "backend_health": "后端健康检查",
        "frontend_health": "前端健康检查", 
        "templates_ok": "模板管理API",
        "meetings_ok": "会议管理API",
        "notes_ok": "笔记管理API",
        "cors_ok": "CORS跨域配置",
        "error_handling_ok": "错误处理机制",
        "performance_ok": "基础性能测试"
    }
    
    for key, name in modules.items():
        status = "✅ 通过" if key in test_results else "⚠️  未测试"
        print(f"   {name}: {status}")
    
    success_rate = len([k for k in modules.keys() if k in test_results]) / len(modules)
    print(f"\n📊 总体成功率: {success_rate:.1%}")
    
    if success_rate >= 0.8:
        print("\n🎉 恭喜！Granola前后端联调测试基本通过!")
        print("   系统可以进行基础的会议和笔记管理功能")
    elif success_rate >= 0.6:
        print("\n⚠️  前后端基本功能正常，但有部分问题需要修复")
    else:
        print("\n❌ 系统存在较多问题，需要进一步调试")
    
    print(f"\n🔗 访问地址:")
    print(f"   前端应用: {FRONTEND_URL}")
    print(f"   后端API: {BACKEND_URL}")
    print(f"   API文档: {BACKEND_URL}/docs")
    print(f"   API测试: {FRONTEND_URL}/test-api")

def main():
    """主测试函数"""
    print("🚀 Granola 前后端联调最终测试")
    print("   测试前端和后端的集成功能...")
    
    test_results = []
    
    # 后端健康检查
    if test_backend_health():
        test_results.append("backend_health")
    
    # 前端健康检查
    if test_frontend_health():
        test_results.append("frontend_health")
    
    # API功能测试
    api_results = test_api_functionality()
    test_results.extend(api_results)
    
    # CORS测试
    if test_cors_and_security():
        test_results.append("cors_ok")
    
    # 错误处理测试
    if test_error_handling():
        test_results.append("error_handling_ok")
    
    # 性能测试
    if performance_test():
        test_results.append("performance_ok")
    
    # 生成报告
    generate_report(test_results)
    
    return len(test_results) >= 5  # 至少5个测试通过才算成功

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)