"""
安全系统测试
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.security import (
    input_validator,
    sql_protector,
    rate_limiter,
    ip_whitelist_manager,
    security_auditor
)


class TestInputValidator:
    """输入验证器测试"""
    
    def test_validate_string_valid(self):
        """测试有效字符串验证"""
        result = input_validator.validate_string(
            "Hello World",
            field_name="test_field"
        )
        
        assert result["valid"] is True
        assert "Hello World" in result["sanitized_value"]
    
    def test_validate_string_xss_detection(self):
        """测试XSS检测"""
        malicious_input = "<script>alert('xss')</script>"
        result = input_validator.validate_string(
            malicious_input,
            field_name="test_field",
            allow_html=False
        )
        
        assert result["valid"] is False
        assert any("恶意代码" in error for error in result["errors"])
    
    def test_validate_string_sql_injection(self):
        """测试SQL注入检测"""
        malicious_input = "'; DROP TABLE users; --"
        result = input_validator.validate_string(
            malicious_input,
            field_name="test_field"
        )
        
        assert result["valid"] is False
        assert any("SQL注入" in error for error in result["errors"])
    
    def test_validate_string_length_limit(self):
        """测试字符串长度限制"""
        long_string = "x" * 1001
        result = input_validator.validate_string(
            long_string,
            field_name="test_field",
            max_length=1000
        )
        
        assert result["valid"] is False
        assert any("长度不能超过" in error for error in result["errors"])
    
    def test_validate_email_valid(self):
        """测试有效邮箱验证"""
        result = input_validator.validate_email("test@example.com")
        
        assert result["valid"] is True
        assert result["normalized_email"] == "test@example.com"
    
    def test_validate_email_invalid(self):
        """测试无效邮箱验证"""
        result = input_validator.validate_email("invalid-email")
        
        assert result["valid"] is False
        assert "errors" in result
    
    def test_validate_password_strong(self):
        """测试强密码验证"""
        result = input_validator.validate_password("StrongP@ssw0rd123")
        
        assert result["valid"] is True
        assert result["strength"] == "strong"
        assert result["score"] >= 5
    
    def test_validate_password_weak(self):
        """测试弱密码验证"""
        result = input_validator.validate_password("123")
        
        assert result["valid"] is False
        assert result["strength"] == "weak"
        assert len(result["errors"]) > 0
    
    def test_validate_password_common_weak(self):
        """测试常见弱密码"""
        result = input_validator.validate_password("password")
        
        assert result["valid"] is False
        assert any("过于简单" in error for error in result["errors"])
    
    def test_validate_file_upload_valid(self):
        """测试有效文件上传验证"""
        result = input_validator.validate_file_upload(
            filename="document.pdf",
            file_size=1024 * 1024,  # 1MB
            allowed_extensions=["pdf", "doc", "txt"],
            max_size=10 * 1024 * 1024  # 10MB
        )
        
        assert result["valid"] is True
        assert result["safe_filename"] == "document.pdf"
    
    def test_validate_file_upload_invalid_extension(self):
        """测试无效文件扩展名"""
        result = input_validator.validate_file_upload(
            filename="malware.exe",
            file_size=1024,
            allowed_extensions=["pdf", "doc", "txt"]
        )
        
        assert result["valid"] is False
        assert any("不支持的文件类型" in error for error in result["errors"])
    
    def test_validate_file_upload_too_large(self):
        """测试文件过大"""
        result = input_validator.validate_file_upload(
            filename="large.pdf",
            file_size=200 * 1024 * 1024,  # 200MB
            max_size=100 * 1024 * 1024   # 100MB限制
        )
        
        assert result["valid"] is False
        assert any("文件大小超过限制" in error for error in result["errors"])
    
    def test_validate_file_upload_dangerous_filename(self):
        """测试危险文件名"""
        result = input_validator.validate_file_upload(
            filename="../../../etc/passwd",
            file_size=1024
        )
        
        assert result["valid"] is False
        assert any("非法字符" in error for error in result["errors"])
    
    def test_validate_ip_address_valid(self):
        """测试有效IP地址验证"""
        result = input_validator.validate_ip_address("192.168.1.1")
        
        assert result["valid"] is True
        assert result["ip_version"] == 4
        assert result["is_private"] is True
    
    def test_validate_ip_address_invalid(self):
        """测试无效IP地址验证"""
        result = input_validator.validate_ip_address("invalid-ip")
        
        assert result["valid"] is False
        assert "errors" in result
    
    def test_validate_url_valid(self):
        """测试有效URL验证"""
        result = input_validator.validate_url("https://example.com/path")
        
        assert result["valid"] is True
    
    def test_validate_url_malicious_protocol(self):
        """测试恶意协议URL"""
        result = input_validator.validate_url("javascript:alert('xss')")
        
        assert result["valid"] is False
        assert any("恶意协议" in error for error in result["errors"])


class TestSQLProtector:
    """SQL保护器测试"""
    
    def test_analyze_safe_query(self):
        """测试安全查询分析"""
        safe_query = "SELECT name, email FROM users WHERE id = ?"
        result = sql_protector.analyze_sql_query(safe_query)
        
        assert result["is_safe"] is True
        assert result["query_type"] == "SELECT"
    
    def test_analyze_dangerous_query(self):
        """测试危险查询分析"""
        dangerous_query = "SELECT * FROM users; DROP TABLE users; --"
        result = sql_protector.analyze_sql_query(dangerous_query)
        
        assert result["is_safe"] is False
        assert len(result["dangerous_tokens"]) > 0
        assert len(result["warnings"]) > 0
    
    def test_analyze_union_injection(self):
        """测试UNION注入检测"""
        injection_query = "SELECT * FROM users WHERE id = 1 UNION SELECT password FROM admin"
        result = sql_protector.analyze_sql_query(injection_query)
        
        assert "UNION" in result["dangerous_tokens"]
    
    def test_sanitize_query_params(self):
        """测试查询参数清理"""
        dirty_params = {
            "name": "<script>alert('xss')</script>",
            "email": "user@example.com",
            "age": 25
        }
        
        clean_params = sql_protector.sanitize_query_params(dirty_params)
        
        assert "<script>" not in clean_params["name"]
        assert clean_params["email"] == "user@example.com"
        assert clean_params["age"] == 25


class TestRateLimiter:
    """速率限制器测试"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_within_limit(self):
        """测试在限制内的请求"""
        with patch.object(rate_limiter, 'cache_manager') as mock_cache:
            # Mock Redis操作
            mock_cache.redis_client.zcount.return_value = 5  # 当前请求数
            mock_cache.redis_client.zadd = AsyncMock()
            mock_cache.redis_client.zremrangebyscore = AsyncMock()
            mock_cache.redis_client.expire = AsyncMock()
            
            result = await rate_limiter.is_rate_limited("test_key", limit=10)
            
            assert result["limited"] is False
            assert result["current_requests"] == 6  # 5 + 1
            assert result["remaining"] == 4  # 10 - 5 - 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """测试超出速率限制"""
        with patch.object(rate_limiter, 'cache_manager') as mock_cache:
            # Mock Redis操作
            mock_cache.redis_client.zcount.return_value = 15  # 超出限制
            mock_cache.redis_client.zrange.return_value = [(b'1234567890', 1234567890)]
            
            result = await rate_limiter.is_rate_limited("test_key", limit=10)
            
            assert result["limited"] is True
            assert result["current_requests"] == 15
            assert "reset_time" in result
    
    @pytest.mark.asyncio
    async def test_burst_limit_check(self):
        """测试突发限制检查"""
        with patch.object(rate_limiter, 'cache_manager') as mock_cache:
            # Mock Redis操作
            mock_cache.redis_client.incr.return_value = 15  # 超出突发限制
            mock_cache.redis_client.expire = AsyncMock()
            
            is_limited = await rate_limiter.check_burst_limit("test_key", limit=10)
            
            assert is_limited is True


class TestIPWhitelistManager:
    """IP白名单管理器测试"""
    
    @pytest.mark.asyncio
    async def test_add_to_whitelist(self):
        """测试添加到白名单"""
        with patch.object(ip_whitelist_manager, 'save_whitelist') as mock_save:
            mock_save.return_value = None
            
            success = await ip_whitelist_manager.add_to_whitelist("192.168.1.1")
            
            assert success is True
            assert "192.168.1.1" in ip_whitelist_manager.whitelist
    
    @pytest.mark.asyncio
    async def test_remove_from_whitelist(self):
        """测试从白名单移除"""
        ip_whitelist_manager.whitelist = ["192.168.1.1", "192.168.1.2"]
        
        with patch.object(ip_whitelist_manager, 'save_whitelist') as mock_save:
            mock_save.return_value = None
            
            success = await ip_whitelist_manager.remove_from_whitelist("192.168.1.1")
            
            assert success is True
            assert "192.168.1.1" not in ip_whitelist_manager.whitelist
            assert "192.168.1.2" in ip_whitelist_manager.whitelist
    
    def test_is_ip_allowed_with_whitelist(self):
        """测试有白名单时的IP检查"""
        ip_whitelist_manager.whitelist = ["192.168.1.0/24", "10.0.0.1"]
        ip_whitelist_manager.blacklist = []
        
        # 白名单中的IP
        assert ip_whitelist_manager.is_ip_allowed("192.168.1.10") is True
        assert ip_whitelist_manager.is_ip_allowed("10.0.0.1") is True
        
        # 不在白名单中的IP
        assert ip_whitelist_manager.is_ip_allowed("8.8.8.8") is False
    
    def test_is_ip_allowed_with_blacklist(self):
        """测试有黑名单时的IP检查"""
        ip_whitelist_manager.whitelist = []  # 无白名单
        ip_whitelist_manager.blacklist = ["192.168.1.0/24", "10.0.0.1"]
        
        # 黑名单中的IP
        assert ip_whitelist_manager.is_ip_allowed("192.168.1.10") is False
        assert ip_whitelist_manager.is_ip_allowed("10.0.0.1") is False
        
        # 不在黑名单中的IP
        assert ip_whitelist_manager.is_ip_allowed("8.8.8.8") is True
    
    def test_is_ip_allowed_no_lists(self):
        """测试无白名单和黑名单时的IP检查"""
        ip_whitelist_manager.whitelist = []
        ip_whitelist_manager.blacklist = []
        
        # 所有IP都应该被允许
        assert ip_whitelist_manager.is_ip_allowed("192.168.1.1") is True
        assert ip_whitelist_manager.is_ip_allowed("8.8.8.8") is True


class TestSecurityAuditor:
    """安全审计器测试"""
    
    @pytest.mark.asyncio
    async def test_log_security_event(self):
        """测试记录安全事件"""
        with patch.object(security_auditor, 'cache_manager') as mock_cache:
            mock_cache.redis_client.lpush = AsyncMock()
            mock_cache.redis_client.ltrim = AsyncMock()
            
            await security_auditor.log_security_event(
                event_type="test_event",
                description="Test security event",
                user_id=123,
                ip_address="192.168.1.1",
                severity="medium"
            )
            
            mock_cache.redis_client.lpush.assert_called_once()
            mock_cache.redis_client.ltrim.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_security_events(self):
        """测试获取安全事件"""
        mock_events = [
            "{'event_type': 'login_failed', 'description': 'Failed login attempt'}",
            "{'event_type': 'rate_limit_exceeded', 'description': 'Rate limit exceeded'}"
        ]
        
        with patch.object(security_auditor, 'cache_manager') as mock_cache:
            mock_cache.redis_client.lrange.return_value = mock_events
            
            events = await security_auditor.get_security_events(limit=10)
            
            assert len(events) == 2
    
    @pytest.mark.asyncio
    async def test_analyze_security_patterns(self):
        """测试安全模式分析"""
        mock_events = [
            {'event_type': 'login_failed', 'ip_address': '192.168.1.1', 'severity': 'medium'},
            {'event_type': 'rate_limit_exceeded', 'ip_address': '192.168.1.1', 'severity': 'high'},
            {'event_type': 'login_failed', 'ip_address': '192.168.1.2', 'severity': 'medium'}
        ]
        
        with patch.object(security_auditor, 'get_security_events') as mock_get_events:
            mock_get_events.return_value = mock_events
            
            analysis = await security_auditor.analyze_security_patterns()
            
            assert analysis["total_events"] == 3
            assert analysis["event_types"]["login_failed"] == 2
            assert analysis["event_types"]["rate_limit_exceeded"] == 1
            assert analysis["top_ips"]["192.168.1.1"] == 2
            assert analysis["severity_distribution"]["medium"] == 2
            assert analysis["severity_distribution"]["high"] == 1


class TestSecurityIntegration:
    """安全系统集成测试"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_input_validation(self):
        """测试综合输入验证"""
        test_cases = [
            # (input, expected_valid)
            ("normal text", True),
            ("<script>alert('xss')</script>", False),
            ("'; DROP TABLE users; --", False),
            ("x" * 5000, False),  # 过长
            ("", False),  # 空字符串（required=True）
        ]
        
        for test_input, expected_valid in test_cases:
            result = input_validator.validate_string(
                test_input,
                field_name="test",
                required=True
            )
            assert result["valid"] == expected_valid, f"Failed for input: {test_input}"
    
    def test_sql_injection_detection_patterns(self):
        """测试SQL注入检测模式"""
        injection_patterns = [
            "1' OR '1'='1",
            "admin'--",
            "'; DROP TABLE users; --",
            "1 UNION SELECT password FROM users",
            "1; INSERT INTO users VALUES('hacker', 'pass')",
            "1' OR 1=1 /*"
        ]
        
        for pattern in injection_patterns:
            result = sql_protector.analyze_sql_query(f"SELECT * FROM users WHERE id = {pattern}")
            assert result["is_safe"] is False, f"Failed to detect injection: {pattern}"
    
    def test_xss_detection_patterns(self):
        """测试XSS检测模式"""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('xss')",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<svg onload='alert(1)'>",
            "<body onload='alert(1)'>"
        ]
        
        for pattern in xss_patterns:
            result = input_validator.validate_string(
                pattern,
                field_name="test",
                allow_html=False
            )
            assert result["valid"] is False, f"Failed to detect XSS: {pattern}"