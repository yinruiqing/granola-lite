#!/usr/bin/env python3
"""
测试代理配置功能
"""

import os
import sys
from unittest.mock import patch, MagicMock
import pytest
import httpx

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import Settings
from app.services.ai.openai_provider import OpenAILLMProvider, OpenAISTTProvider


def test_proxy_config_loading():
    """测试代理配置加载"""
    
    # 模拟环境变量
    with patch.dict(os.environ, {
        'HTTP_PROXY': 'http://proxy.example.com:8080',
        'HTTPS_PROXY': 'http://proxy.example.com:8080',
        'PROXY_AUTH': 'testuser:testpass'
    }):
        settings = Settings()
        
        assert settings.http_proxy == 'http://proxy.example.com:8080'
        assert settings.https_proxy == 'http://proxy.example.com:8080'
        assert settings.proxy_auth == 'testuser:testpass'


def test_openai_llm_provider_with_proxy():
    """测试OpenAI LLM提供商的代理配置"""
    
    config = {
        'api_key': 'test-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'http_proxy': 'http://proxy.example.com:8080',
        'https_proxy': 'http://proxy.example.com:8080',
        'proxy_auth': 'user:pass'
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        provider = OpenAILLMProvider(config)
        
        # 验证httpx.AsyncClient被正确调用
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        
        # 检查代理配置
        assert 'proxies' in call_kwargs
        proxies = call_kwargs['proxies']
        assert proxies['http://'] == 'http://proxy.example.com:8080'
        assert proxies['https://'] == 'http://proxy.example.com:8080'
        
        # 检查认证配置
        assert 'auth' in call_kwargs
        assert call_kwargs['auth'] == ('user', 'pass')


def test_openai_stt_provider_with_proxy():
    """测试OpenAI STT提供商的代理配置"""
    
    config = {
        'api_key': 'test-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'whisper-1',
        'http_proxy': 'http://proxy.example.com:8080',
        'https_proxy': 'http://proxy.example.com:8080',
        'proxy_auth': 'user:pass'
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        provider = OpenAISTTProvider(config)
        
        # 验证httpx.AsyncClient被正确调用
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        
        # 检查代理配置
        assert 'proxies' in call_kwargs
        proxies = call_kwargs['proxies']
        assert proxies['http://'] == 'http://proxy.example.com:8080'
        assert proxies['https://'] == 'http://proxy.example.com:8080'


def test_no_proxy_config():
    """测试没有代理配置的情况"""
    
    config = {
        'api_key': 'test-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini'
    }
    
    with patch('app.services.ai.openai_provider.AsyncOpenAI') as mock_openai:
        provider = OpenAILLMProvider(config)
        
        # 验证AsyncOpenAI被正确调用，没有http_client参数
        mock_openai.assert_called_once_with(
            api_key='test-key',
            base_url='https://api.openai.com/v1',
            timeout=60,
            http_client=None
        )


def test_partial_proxy_config():
    """测试部分代理配置"""
    
    config = {
        'api_key': 'test-key',
        'base_url': 'https://api.openai.com/v1',
        'model': 'gpt-4o-mini',
        'http_proxy': 'http://proxy.example.com:8080'
        # 没有https_proxy和proxy_auth
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        provider = OpenAILLMProvider(config)
        
        # 验证httpx.AsyncClient被正确调用
        mock_client.assert_called_once()
        call_kwargs = mock_client.call_args[1]
        
        # 检查代理配置
        assert 'proxies' in call_kwargs
        proxies = call_kwargs['proxies']
        assert proxies['http://'] == 'http://proxy.example.com:8080'
        assert 'https://' not in proxies
        
        # 检查没有认证配置
        assert call_kwargs['auth'] is None


def test_ai_config_with_proxy():
    """测试AI配置包含代理设置"""
    
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-key',
        'HTTP_PROXY': 'http://proxy.example.com:8080',
        'HTTPS_PROXY': 'http://proxy.example.com:8080',
        'PROXY_AUTH': 'user:pass'
    }):
        settings = Settings()
        ai_config = settings.ai_config
        
        # 检查STT配置包含代理设置
        stt_config = ai_config.stt_config
        assert stt_config['http_proxy'] == 'http://proxy.example.com:8080'
        assert stt_config['https_proxy'] == 'http://proxy.example.com:8080'
        assert stt_config['proxy_auth'] == 'user:pass'
        
        # 检查LLM配置包含代理设置
        llm_config = ai_config.llm_config
        assert llm_config['http_proxy'] == 'http://proxy.example.com:8080'
        assert llm_config['https_proxy'] == 'http://proxy.example.com:8080'
        assert llm_config['proxy_auth'] == 'user:pass'


def print_test_results():
    """运行所有测试并打印结果"""
    print("🧪 代理配置测试")
    print("="*50)
    
    tests = [
        ("代理配置加载测试", test_proxy_config_loading),
        ("OpenAI LLM代理配置测试", test_openai_llm_provider_with_proxy),
        ("OpenAI STT代理配置测试", test_openai_stt_provider_with_proxy),
        ("无代理配置测试", test_no_proxy_config),
        ("部分代理配置测试", test_partial_proxy_config),
        ("AI配置代理集成测试", test_ai_config_with_proxy)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name} - 通过")
            passed += 1
        except Exception as e:
            print(f"❌ {test_name} - 失败: {e}")
            failed += 1
    
    print(f"\n📊 测试结果: {passed}个通过, {failed}个失败")
    
    if failed == 0:
        print("🎉 所有代理配置测试通过！")
        return True
    else:
        print("⚠️ 部分测试失败，请检查代理配置实现")
        return False


if __name__ == "__main__":
    success = print_test_results()
    sys.exit(0 if success else 1)