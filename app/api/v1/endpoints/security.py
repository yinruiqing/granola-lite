"""
安全管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator
from datetime import datetime

from app.db.database import get_db
from app.core.auth import require_admin_user, get_current_user
from app.core.security import (
    input_validator,
    sql_protector,
    rate_limiter,
    ip_whitelist_manager,
    security_auditor
)
from app.models.user import User
from loguru import logger


router = APIRouter()


class ValidationRequest(BaseModel):
    """验证请求模型"""
    input_type: str  # string, email, password, file, url, ip
    value: str
    options: Dict[str, Any] = {}


class RateLimitRequest(BaseModel):
    """速率限制请求模型"""
    key: str
    limit: Optional[int] = None
    window: Optional[int] = None


class IPManagementRequest(BaseModel):
    """IP管理请求模型"""
    ip_address: str
    action: str  # add, remove
    list_type: str  # whitelist, blacklist
    
    @validator('ip_address')
    def validate_ip(cls, v):
        # 基本IP格式验证
        if not v:
            raise ValueError('IP地址不能为空')
        return v


class SQLAnalysisRequest(BaseModel):
    """SQL分析请求模型"""
    query: str


class SecurityConfigRequest(BaseModel):
    """安全配置请求模型"""
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    ip_whitelist_enabled: bool = False
    csrf_protection_enabled: bool = True
    input_validation_enabled: bool = True


# ==================== 输入验证 ====================

@router.post("/validation/validate-input", summary="验证输入数据")
async def validate_input_data(
    request: ValidationRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    验证各种类型的输入数据
    
    - **input_type**: 输入类型 (string, email, password, file, url, ip)
    - **value**: 要验证的值
    - **options**: 验证选项
    """
    try:
        result = {"input_type": request.input_type, "value": request.value}
        
        if request.input_type == "string":
            validation_result = input_validator.validate_string(
                request.value,
                field_name=request.options.get("field_name", "input"),
                max_length=request.options.get("max_length"),
                allow_html=request.options.get("allow_html", False),
                required=request.options.get("required", True)
            )
            result.update(validation_result)
            
        elif request.input_type == "email":
            validation_result = input_validator.validate_email(request.value)
            result.update(validation_result)
            
        elif request.input_type == "password":
            validation_result = input_validator.validate_password(request.value)
            result.update(validation_result)
            
        elif request.input_type == "url":
            validation_result = input_validator.validate_url(request.value)
            result.update(validation_result)
            
        elif request.input_type == "ip":
            validation_result = input_validator.validate_ip_address(request.value)
            result.update(validation_result)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的输入类型: {request.input_type}"
            )
        
        return {
            "success": True,
            "validation_result": result
        }
        
    except Exception as e:
        logger.error(f"输入验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"输入验证失败: {str(e)}"
        )


@router.post("/validation/analyze-sql", summary="分析SQL查询安全性")
async def analyze_sql_query(
    request: SQLAnalysisRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    分析SQL查询的安全性（需要管理员权限）
    
    - **query**: 要分析的SQL查询
    """
    try:
        analysis_result = sql_protector.analyze_sql_query(request.query)
        
        return {
            "success": True,
            "sql_analysis": analysis_result,
            "query_sample": request.query[:100] + "..." if len(request.query) > 100 else request.query
        }
        
    except Exception as e:
        logger.error(f"SQL分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SQL分析失败: {str(e)}"
        )


# ==================== 速率限制 ====================

@router.post("/rate-limit/check", summary="检查速率限制")
async def check_rate_limit(
    request: RateLimitRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    检查指定键的速率限制状态（需要管理员权限）
    
    - **key**: 限制键
    - **limit**: 速率限制（每分钟请求数）
    - **window**: 时间窗口（秒）
    """
    try:
        rate_limit_result = await rate_limiter.is_rate_limited(
            key=request.key,
            limit=request.limit,
            window=request.window
        )
        
        return {
            "success": True,
            "rate_limit_status": rate_limit_result
        }
        
    except Exception as e:
        logger.error(f"速率限制检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"速率限制检查失败: {str(e)}"
        )


@router.post("/rate-limit/reset", summary="重置速率限制")
async def reset_rate_limit(
    key: str = Query(..., description="要重置的限制键"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    重置指定键的速率限制（需要管理员权限）
    
    - **key**: 限制键
    """
    try:
        # 删除Redis中的限制记录
        from app.core.cache import cache_manager
        
        deleted = await cache_manager.redis_client.delete(f"rate_limit:{key}")
        burst_deleted = await cache_manager.redis_client.delete(f"burst_limit:{key}")
        
        return {
            "success": True,
            "message": f"速率限制已重置: {key}",
            "deleted_entries": deleted + burst_deleted
        }
        
    except Exception as e:
        logger.error(f"重置速率限制失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重置速率限制失败: {str(e)}"
        )


# ==================== IP管理 ====================

@router.post("/ip-management/manage", summary="管理IP白名单/黑名单")
async def manage_ip_lists(
    request: IPManagementRequest,
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    管理IP白名单和黑名单（需要管理员权限）
    
    - **ip_address**: IP地址或CIDR网络
    - **action**: 操作类型 (add, remove)
    - **list_type**: 列表类型 (whitelist, blacklist)
    """
    try:
        success = False
        message = ""
        
        if request.list_type == "whitelist":
            if request.action == "add":
                success = await ip_whitelist_manager.add_to_whitelist(request.ip_address)
                message = f"已添加到白名单: {request.ip_address}" if success else "添加失败"
            elif request.action == "remove":
                success = await ip_whitelist_manager.remove_from_whitelist(request.ip_address)
                message = f"已从白名单移除: {request.ip_address}" if success else "移除失败"
        
        elif request.list_type == "blacklist":
            if request.action == "add":
                success = await ip_whitelist_manager.add_to_blacklist(request.ip_address)
                message = f"已添加到黑名单: {request.ip_address}" if success else "添加失败"
            # 黑名单移除功能需要实现
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的列表类型: {request.list_type}"
            )
        
        # 记录安全事件
        await security_auditor.log_security_event(
            event_type="ip_list_management",
            description=f"{request.action} {request.ip_address} to {request.list_type}",
            user_id=current_user.id,
            severity="medium"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message
            )
        
        return {
            "success": True,
            "message": message,
            "operation": {
                "action": request.action,
                "ip_address": request.ip_address,
                "list_type": request.list_type
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP管理操作失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IP管理操作失败: {str(e)}"
        )


@router.get("/ip-management/lists", summary="获取IP列表")
async def get_ip_lists(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取IP白名单和黑名单（需要管理员权限）
    """
    try:
        # 加载最新的白名单
        await ip_whitelist_manager.load_whitelist()
        
        return {
            "success": True,
            "ip_lists": {
                "whitelist": ip_whitelist_manager.whitelist,
                "blacklist": ip_whitelist_manager.blacklist,
                "whitelist_count": len(ip_whitelist_manager.whitelist),
                "blacklist_count": len(ip_whitelist_manager.blacklist)
            }
        }
        
    except Exception as e:
        logger.error(f"获取IP列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取IP列表失败: {str(e)}"
        )


@router.post("/ip-management/check", summary="检查IP访问权限")
async def check_ip_access(
    ip_address: str = Query(..., description="要检查的IP地址"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    检查IP地址的访问权限（需要管理员权限）
    
    - **ip_address**: 要检查的IP地址
    """
    try:
        # 验证IP格式
        validation_result = input_validator.validate_ip_address(ip_address)
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的IP地址: {validation_result['errors'][0]}"
            )
        
        # 检查访问权限
        is_allowed = ip_whitelist_manager.is_ip_allowed(ip_address)
        
        return {
            "success": True,
            "ip_check": {
                "ip_address": ip_address,
                "is_allowed": is_allowed,
                "ip_info": validation_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"IP访问权限检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IP访问权限检查失败: {str(e)}"
        )


# ==================== 安全审计 ====================

@router.get("/audit/events", summary="获取安全事件")
async def get_security_events(
    limit: int = Query(100, description="返回事件数量限制"),
    event_type: Optional[str] = Query(None, description="事件类型过滤"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取安全审计事件（需要管理员权限）
    
    - **limit**: 返回事件数量限制
    - **event_type**: 事件类型过滤
    """
    try:
        events = await security_auditor.get_security_events(
            limit=limit,
            event_type=event_type
        )
        
        return {
            "success": True,
            "security_events": events,
            "count": len(events),
            "filter": {
                "limit": limit,
                "event_type": event_type
            }
        }
        
    except Exception as e:
        logger.error(f"获取安全事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取安全事件失败: {str(e)}"
        )


@router.get("/audit/analysis", summary="安全模式分析")
async def get_security_analysis(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取安全模式分析（需要管理员权限）
    """
    try:
        analysis = await security_auditor.analyze_security_patterns()
        
        return {
            "success": True,
            "security_analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"安全模式分析失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"安全模式分析失败: {str(e)}"
        )


@router.post("/audit/log-event", summary="手动记录安全事件")
async def log_security_event(
    event_type: str = Query(..., description="事件类型"),
    description: str = Query(..., description="事件描述"),
    severity: str = Query("medium", description="严重程度"),
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    手动记录安全事件（需要管理员权限）
    
    - **event_type**: 事件类型
    - **description**: 事件描述
    - **severity**: 严重程度 (low, medium, high, critical)
    """
    try:
        await security_auditor.log_security_event(
            event_type=event_type,
            description=description,
            user_id=current_user.id,
            severity=severity
        )
        
        return {
            "success": True,
            "message": "安全事件已记录",
            "event": {
                "type": event_type,
                "description": description,
                "severity": severity,
                "logged_by": current_user.id,
                "timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"记录安全事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"记录安全事件失败: {str(e)}"
        )


# ==================== 安全配置 ====================

@router.get("/config/status", summary="获取安全配置状态")
async def get_security_config_status(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取当前安全配置状态（需要管理员权限）
    """
    try:
        # 这里应该从配置文件或数据库读取实际配置
        # 现在返回默认配置状态
        config_status = {
            "rate_limiting": {
                "enabled": True,
                "default_limit": 100,
                "burst_limit": 10
            },
            "ip_filtering": {
                "whitelist_enabled": len(ip_whitelist_manager.whitelist) > 0,
                "blacklist_enabled": len(ip_whitelist_manager.blacklist) > 0,
                "whitelist_count": len(ip_whitelist_manager.whitelist),
                "blacklist_count": len(ip_whitelist_manager.blacklist)
            },
            "input_validation": {
                "enabled": True,
                "max_string_length": input_validator.max_string_length,
                "max_file_size": input_validator.max_file_size
            },
            "security_headers": {
                "enabled": True,
                "headers": [
                    "X-Content-Type-Options",
                    "X-Frame-Options", 
                    "X-XSS-Protection",
                    "Strict-Transport-Security",
                    "Content-Security-Policy"
                ]
            }
        }
        
        return {
            "success": True,
            "security_config": config_status,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取安全配置状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取安全配置状态失败: {str(e)}"
        )


@router.get("/security-report", summary="生成安全报告")
async def generate_security_report(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    生成综合安全报告（需要管理员权限）
    """
    try:
        # 获取各种安全数据
        security_events = await security_auditor.get_security_events(limit=1000)
        security_analysis = await security_auditor.analyze_security_patterns()
        
        # 计算安全评分
        security_score = 100
        issues = []
        
        # 基于安全事件扣分
        high_severity_events = len([e for e in security_events if e.get('severity') == 'high'])
        critical_events = len([e for e in security_events if e.get('severity') == 'critical'])
        
        security_score -= high_severity_events * 2
        security_score -= critical_events * 5
        
        if high_severity_events > 0:
            issues.append(f"{high_severity_events} 个高严重性安全事件")
        if critical_events > 0:
            issues.append(f"{critical_events} 个严重安全事件")
        
        # 基于频繁的IP活动扣分
        top_ips = security_analysis.get("top_ips", {})
        if top_ips:
            max_requests = max(top_ips.values())
            if max_requests > 100:
                security_score -= 5
                issues.append(f"检测到高频IP活动 (最高: {max_requests} 次)")
        
        # 确保分数在0-100范围内
        security_score = max(0, min(100, security_score))
        
        # 确定安全等级
        if security_score >= 90:
            security_grade = "优秀"
            grade_color = "green"
        elif security_score >= 80:
            security_grade = "良好"
            grade_color = "blue"
        elif security_score >= 70:
            security_grade = "一般"
            grade_color = "yellow"
        elif security_score >= 60:
            security_grade = "较差"
            grade_color = "orange"
        else:
            security_grade = "差"
            grade_color = "red"
        
        security_report = {
            "summary": {
                "security_score": security_score,
                "security_grade": security_grade,
                "grade_color": grade_color,
                "total_events": len(security_events),
                "issues_count": len(issues),
                "issues": issues
            },
            "event_analysis": security_analysis,
            "recommendations": [
                "定期检查安全事件日志",
                "保持IP白名单和黑名单更新",
                "监控高频访问IP地址",
                "定期更新安全配置"
            ],
            "recent_events": security_events[:10],
            "generated_at": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "security_report": security_report,
            "message": f"安全报告生成完成，安全评分: {security_score} ({security_grade})"
        }
        
    except Exception as e:
        logger.error(f"生成安全报告失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成安全报告失败: {str(e)}"
        )