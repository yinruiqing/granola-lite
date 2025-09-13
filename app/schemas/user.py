"""
用户数据传输模式
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模式"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class UserCreate(BaseModel):
    """用户创建模式"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class UserUpdate(BaseModel):
    """用户更新模式"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


class UserInDB(UserBase):
    """数据库中的用户模式"""
    id: int
    hashed_password: str
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """用户响应模式"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """用户登录模式"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserRegister(BaseModel):
    """用户注册模式"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = Field(None, max_length=100)


class TokenResponse(BaseModel):
    """令牌响应模式"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模式"""
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """密码修改请求模式"""
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class PasswordResetRequest(BaseModel):
    """密码重置请求模式"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """密码重置确认模式"""
    token: str
    new_password: str = Field(..., min_length=6, max_length=100)


class EmailVerificationRequest(BaseModel):
    """邮箱验证请求模式"""
    email: EmailStr


class EmailVerificationConfirm(BaseModel):
    """邮箱验证确认模式"""
    token: str