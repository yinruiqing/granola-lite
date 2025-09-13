"""
认证系统测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.auth import verify_password, get_password_hash, create_access_token, verify_token


class TestAuthentication:
    """认证功能测试"""
    
    @pytest.mark.asyncio
    async def test_user_registration(self, client: AsyncClient):
        """测试用户注册"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "newpassword123"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["success"] is True
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["username"] == user_data["username"]
        assert "access_token" in data
    
    @pytest.mark.asyncio
    async def test_user_login(self, client: AsyncClient, test_user: User):
        """测试用户登录"""
        login_data = {
            "email": test_user.email,
            "password": "testpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """测试无效凭据登录"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict, test_user: User):
        """测试获取当前用户信息"""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["user"]["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """测试未授权访问"""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_password_hashing(self):
        """测试密码哈希"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False
    
    @pytest.mark.asyncio
    async def test_token_creation_and_verification(self, test_user: User):
        """测试JWT令牌创建和验证"""
        token = create_access_token(data={"sub": test_user.email})
        assert token is not None
        
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_password_change(
        self, 
        client: AsyncClient, 
        auth_headers: dict, 
        test_user: User
    ):
        """测试密码修改"""
        change_data = {
            "old_password": "testpassword",
            "new_password": "newtestpassword123"
        }
        
        response = await client.post(
            "/api/v1/auth/change-password",
            json=change_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_duplicate_email_registration(self, client: AsyncClient, test_user: User):
        """测试重复邮箱注册"""
        user_data = {
            "email": test_user.email,  # 使用已存在的邮箱
            "username": "anotheruser",
            "full_name": "Another User",
            "password": "anotherpassword"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
        assert "already exists" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_weak_password_validation(self, client: AsyncClient):
        """测试弱密码验证"""
        user_data = {
            "email": "weakpassword@example.com",
            "username": "weakuser",
            "full_name": "Weak User",
            "password": "123"  # 弱密码
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        
        data = response.json()
        assert data["success"] is False
    
    @pytest.mark.asyncio
    async def test_admin_required_endpoint(
        self, 
        client: AsyncClient, 
        auth_headers: dict,
        admin_auth_headers: dict
    ):
        """测试需要管理员权限的端点"""
        # 普通用户访问
        response = await client.get("/api/v1/security/audit/events", headers=auth_headers)
        assert response.status_code == 403
        
        # 管理员用户访问
        response = await client.get("/api/v1/security/audit/events", headers=admin_auth_headers)
        assert response.status_code == 200


class TestAuthMiddleware:
    """认证中间件测试"""
    
    @pytest.mark.asyncio
    async def test_token_in_header(self, client: AsyncClient, test_user: User):
        """测试头部中的令牌"""
        token = create_access_token(data={"sub": test_user.email})
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client: AsyncClient):
        """测试无效令牌格式"""
        headers = {"Authorization": "Invalid token"}
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_expired_token(self, client: AsyncClient, test_user: User):
        """测试过期令牌"""
        # 创建已过期的令牌（负数过期时间）
        from datetime import timedelta
        token = create_access_token(
            data={"sub": test_user.email},
            expires_delta=timedelta(minutes=-30)
        )
        headers = {"Authorization": f"Bearer {token}"}
        
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401