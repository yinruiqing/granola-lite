#!/usr/bin/env python3
"""
运行所有测试的脚本
"""

import subprocess
import sys
import os

def run_test(test_file, description):
    """运行单个测试文件"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print(f"✅ {description} - 通过")
            if result.stdout:
                print(result.stdout)
        else:
            print(f"❌ {description} - 失败")
            if result.stderr:
                print("错误输出:")
                print(result.stderr)
            if result.stdout:
                print("标准输出:")
                print(result.stdout)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ {description} - 执行失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 Granola 测试套件")
    print("   运行所有测试...")
    
    tests = [
        ("test_integration.py", "前后端集成测试"),
        ("final_test.py", "综合联调测试"),
        ("test_proxy_config.py", "代理配置测试")
    ]
    
    results = []
    for test_file, description in tests:
        success = run_test(test_file, description)
        results.append((description, success))
    
    # 生成总结报告
    print(f"\n{'='*60}")
    print("  测试总结报告")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {description}: {status}")
    
    print(f"\n📊 总体结果: {passed}/{total} 测试通过")
    success_rate = passed / total if total > 0 else 0
    
    if success_rate == 1.0:
        print("🎉 所有测试通过！系统运行正常。")
        exit_code = 0
    elif success_rate >= 0.8:
        print("⚠️  大部分测试通过，但有少量问题需要关注。")
        exit_code = 1
    else:
        print("❌ 多个测试失败，系统可能存在问题。")
        exit_code = 1
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()