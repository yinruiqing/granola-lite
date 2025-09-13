"""
身份验证相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta
from typing import Dict, Any

from app.db.database import get_db
from app.core.auth import auth_service, get_current_user, require_current_user
from app.core.events import event_emitter, Events
from app.schemas.user import (
    UserLogin, UserRegister, TokenResponse, RefreshTokenRequest,
    UserResponse, PasswordChangeRequest, UserUpdate
)
from app.models.user import User
from loguru import logger

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=Dict[str, Any], summary="用户注册")
async def register(
    user_data: UserRegister,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    用户注册
    
    - **email**: 用户邮箱
    - **username**: 用户名（3-50个字符）
    - **password**: 密码（最少6个字符）
    - **full_name**: 全名（可选）
    """
    try:
        # 创建用户
        user = await auth_service.create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # 发射用户注册事件
        await event_emitter.emit(Events.USER_LOGIN, {
            'user_id': user.id,
            'action': 'register',
            'email': user.email
        })
        
        # 创建访问令牌
        access_token = auth_service.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        refresh_token = auth_service.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        return {
            "success": True,
            "message": "用户注册成功",
            "user": UserResponse.from_orm(user),
            "tokens": TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=auth_service.access_token_expire_minutes * 60
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册过程中发生错误"
        )


@router.post("/login", response_model=Dict[str, Any], summary="用户登录")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    用户登录
    
    - **email**: 用户邮箱
    - **password**: 密码
    """
    # 验证用户凭据
    user = await auth_service.authenticate_user(
        db=db,
        email=login_data.email,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户已被禁用"
        )
    
    # 更新最后登录时间
    from datetime import datetime
    user.last_login_at = datetime.now()
    await db.commit()
    
    # 发射登录事件
    await event_emitter.emit(Events.USER_LOGIN, {
        'user_id': user.id,
        'action': 'login',
        'email': user.email
    })
    
    # 创建令牌
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    refresh_token = auth_service.create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "success": True,
        "message": "登录成功",
        "user": UserResponse.from_orm(user),
        "tokens": TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=auth_service.access_token_expire_minutes * 60
        )
    }


@router.post("/refresh", response_model=Dict[str, Any], summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    使用刷新令牌获取新的访问令牌
    
    - **refresh_token**: 刷新令牌
    """
    # 验证刷新令牌
    payload = auth_service.verify_token(refresh_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌载荷无效"
        )
    
    # 获取用户信息
    try:
        user_id = int(user_id)
        user = await auth_service.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID"
        )
    
    # 创建新的访问令牌
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": auth_service.access_token_expire_minutes * 60
    }


@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(require_current_user)
) -> Dict[str, Any]:
    """
    用户登出
    
    注意：由于JWT是无状态的，这个端点主要用于：
    1. 记录登出事件
    2. 客户端应该删除本地存储的令牌
    """
    # 发射登出事件
    await event_emitter.emit(Events.USER_LOGOUT, {
        'user_id': current_user.id,
        'email': current_user.email
    })
    
    return {
        "success": True,
        "message": "登出成功"
    }


@router.get("/me", response_model=Dict[str, Any], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(require_current_user)
) -> Dict[str, Any]:
    """获取当前登录用户的信息"""
    return {
        "success": True,
        "user": UserResponse.from_orm(current_user)
    }


@router.put("/me", response_model=Dict[str, Any], summary="更新用户信息")
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    更新当前用户的信息
    
    - **email**: 新邮箱（如果修改邮箱，需要重新验证）
    - **username**: 新用户名
    - **full_name**: 全名
    - **avatar_url**: 头像URL
    - **bio**: 个人简介
    """
    try:
        # 更新用户信息
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        # 如果修改了邮箱，需要重新验证
        if 'email' in update_data:
            current_user.is_verified = False
        
        await db.commit()
        await db.refresh(current_user)
        
        return {
            "success": True,
            "message": "用户信息更新成功",
            "user": UserResponse.from_orm(current_user)
        }
        
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    修改用户密码
    
    - **current_password**: 当前密码
    - **new_password**: 新密码（最少6个字符）
    """
    # 验证当前密码
    if not auth_service.verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前密码错误"
        )
    
    # 更新密码
    try:
        current_user.hashed_password = auth_service.get_password_hash(password_data.new_password)
        await db.commit()
        
        # 记录密码修改事件
        logger.info(f"用户 {current_user.id} 修改了密码")
        
        return {
            "success": True,
            "message": "密码修改成功"
        }
        
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )


@router.get("/verify-token", summary="验证令牌")
async def verify_token(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证当前令牌是否有效
    
    如果令牌有效，返回用户信息；否则返回错误
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期"
        )
    
    return {
        "success": True,
        "valid": True,
        "user": UserResponse.from_orm(current_user)
    }