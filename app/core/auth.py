"""
身份验证和授权系统
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserInDB
from loguru import logger

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token schema
security = HTTPBearer(auto_error=False)


class AuthService:
    """身份验证服务"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
        
    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
            
        to_encode.update({"exp": expire, "type": "access"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
        
    def create_refresh_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=30)  # 30天过期
            
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
        
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                return None
                
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"JWT decode error: {e}")
            return None
            
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """通过邮箱获取用户"""
        from sqlalchemy import select
        
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()
        
    async def get_user_by_id(self, db: AsyncSession, user_id: int) -> Optional[User]:
        """通过ID获取用户"""
        from sqlalchemy import select
        
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()
        
    async def authenticate_user(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """验证用户凭据"""
        user = await self.get_user_by_email(db, email)
        if not user:
            return None
            
        if not self.verify_password(password, user.hashed_password):
            return None
            
        return user
        
    async def create_user(
        self, db: AsyncSession, email: str, username: str, password: str, 
        full_name: Optional[str] = None
    ) -> User:
        """创建新用户"""
        from sqlalchemy import select
        
        # 检查邮箱是否已存在
        existing_user = await self.get_user_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
            
        # 检查用户名是否已存在
        result = await db.execute(select(User).filter(User.username == username))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # 创建新用户
        hashed_password = self.get_password_hash(password)
        new_user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            is_active=True,
            is_verified=False  # 需要邮箱验证
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return new_user


# 全局认证服务实例
auth_service = AuthService()


async def get_current_user_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """获取当前用户令牌"""
    if not credentials:
        return None
    return credentials.credentials


async def get_current_user(
    token: Optional[str] = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """获取当前用户（可选）"""
    if not token:
        return None
        
    payload = auth_service.verify_token(token)
    if not payload:
        return None
        
    user_id = payload.get("sub")
    if not user_id:
        return None
        
    try:
        user_id = int(user_id)
        user = await auth_service.get_user_by_id(db, user_id)
        return user
    except (ValueError, TypeError):
        return None


async def require_current_user(
    token: Optional[str] = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    """要求当前用户（必须登录）"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_id = int(user_id)
        user = await auth_service.get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
        
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_admin_user(
    current_user: User = Depends(require_current_user)
) -> User:
    """要求管理员用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def require_verified_user(
    current_user: User = Depends(require_current_user)
) -> User:
    """要求已验证的用户"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )
    return current_user


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, required_permissions: list = None):
        self.required_permissions = required_permissions or []
        
    def __call__(self, current_user: User = Depends(require_current_user)) -> User:
        """检查用户权限"""
        # 超级用户拥有所有权限
        if current_user.is_superuser:
            return current_user
            
        # 这里可以扩展更复杂的权限检查逻辑
        # 例如：检查用户角色、权限表等
        
        return current_user


def require_permissions(*permissions):
    """要求特定权限装饰器"""
    return PermissionChecker(list(permissions))