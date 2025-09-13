"""
模板相关API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Dict, Any, Optional

from app.services.template import get_template_service, TemplateService
from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplateListResponse,
    TemplateCategoriesResponse,
    TemplateDuplicateRequest,
    TEMPLATE_CATEGORIES
)


router = APIRouter()


@router.post("/", summary="创建模板")
async def create_template(
    request: TemplateCreate,
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    创建新的会议模板
    
    - **name**: 模板名称，必须唯一
    - **description**: 模板描述
    - **category**: 模板分类（如：1on1、retrospective、interview等）
    - **structure**: 模板结构定义，JSON格式
    - **prompt_template**: AI处理时使用的提示模板
    - **is_default**: 是否设为该分类的默认模板
    """
    result = await service.create_template(
        name=request.name,
        description=request.description,
        category=request.category,
        structure=request.structure,
        prompt_template=request.prompt_template,
        is_default=request.is_default
    )
    
    return {
        "success": True,
        "message": "模板创建成功",
        "data": result
    }


@router.get("/{template_id}", summary="获取模板详情")
async def get_template(
    template_id: int = Path(..., description="模板ID"),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """获取指定模板的详细信息"""
    result = await service.get_template(template_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {
        "success": True,
        "data": result
    }


@router.get("/", summary="获取模板列表")
async def get_templates(
    category: Optional[str] = Query(None, description="分类筛选"),
    is_default: Optional[bool] = Query(None, description="默认状态筛选"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=200),
    offset: int = Query(0, description="偏移量", ge=0),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    获取模板列表
    
    - **category**: 按分类筛选（可选）
    - **is_default**: 筛选默认模板（可选）
    - **limit**: 返回数量限制
    - **offset**: 偏移量，用于分页
    """
    result = await service.get_templates(
        category=category,
        is_default=is_default,
        limit=limit,
        offset=offset
    )
    
    return {
        "success": True,
        "data": result
    }


@router.put("/{template_id}", summary="更新模板")
async def update_template(
    template_id: int = Path(..., description="模板ID"),
    request: TemplateUpdate,
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    更新模板信息
    
    - 只需提供要更新的字段
    - 如果设置为默认模板，会自动取消同分类下其他默认模板
    """
    result = await service.update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        category=request.category,
        structure=request.structure,
        prompt_template=request.prompt_template,
        is_default=request.is_default
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {
        "success": True,
        "message": "模板更新成功",
        "data": result
    }


@router.delete("/{template_id}", summary="删除模板")
async def delete_template(
    template_id: int = Path(..., description="模板ID"),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    删除模板
    
    注意：如果有会议正在使用此模板，删除会失败
    """
    success = await service.delete_template(template_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在或删除失败")
    
    return {
        "success": True,
        "message": "模板删除成功"
    }


@router.get("/categories/list", summary="获取模板分类列表")
async def get_template_categories(
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    获取所有模板分类及统计信息
    
    返回每个分类下的模板数量和默认模板数量
    """
    result = await service.get_categories()
    
    return {
        "success": True,
        "data": {
            "categories": result,
            "total_categories": len(result),
            "available_categories": TEMPLATE_CATEGORIES
        }
    }


@router.get("/categories/{category}/default", summary="获取分类默认模板")
async def get_default_template(
    category: str = Path(..., description="模板分类"),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """获取指定分类的默认模板"""
    result = await service.get_default_template(category)
    
    if not result:
        raise HTTPException(
            status_code=404, 
            detail=f"分类 '{category}' 没有设置默认模板"
        )
    
    return {
        "success": True,
        "data": result
    }


@router.post("/{template_id}/duplicate", summary="复制模板")
async def duplicate_template(
    template_id: int = Path(..., description="模板ID"),
    request: TemplateDuplicateRequest = TemplateDuplicateRequest(),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    复制模板
    
    - **new_name**: 新模板名称，不提供则自动生成
    
    复制的模板不会设置为默认模板
    """
    result = await service.duplicate_template(
        template_id=template_id,
        new_name=request.new_name
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="源模板不存在")
    
    return {
        "success": True,
        "message": "模板复制成功",
        "data": result
    }


@router.get("/{template_id}/usage", summary="获取模板使用统计")
async def get_template_usage_stats(
    template_id: int = Path(..., description="模板ID"),
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    获取模板使用统计信息
    
    显示有多少会议使用了此模板
    """
    # 验证模板是否存在
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    # TODO: 实现使用统计查询
    # 这里需要查询 meetings 表中使用此模板的记录
    from app.db.session import AsyncSessionLocal
    from app.models.meeting import Meeting
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    
    async with AsyncSessionLocal() as session:
        # 查询总使用次数
        total_result = await session.execute(
            select(func.count(Meeting.id)).where(Meeting.template_id == template_id)
        )
        total_meetings = total_result.scalar() or 0
        
        # 查询最近30天使用次数
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_result = await session.execute(
            select(func.count(Meeting.id)).where(
                Meeting.template_id == template_id,
                Meeting.created_at >= thirty_days_ago
            )
        )
        recent_meetings = recent_result.scalar() or 0
        
        # 查询最后使用时间
        last_used_result = await session.execute(
            select(func.max(Meeting.created_at)).where(Meeting.template_id == template_id)
        )
        last_used = last_used_result.scalar()
    
    return {
        "success": True,
        "data": {
            "template_id": template_id,
            "template_name": template["name"],
            "total_meetings": total_meetings,
            "recent_meetings": recent_meetings,
            "last_used": last_used
        }
    }


@router.post("/validate", summary="验证模板结构")
async def validate_template_structure(
    request: TemplateCreate,
    service: TemplateService = Depends(get_template_service)
) -> Dict[str, Any]:
    """
    验证模板结构的有效性
    
    检查模板的结构定义和提示模板是否符合要求
    """
    errors = []
    warnings = []
    
    # 基础验证
    if not request.name or len(request.name.strip()) == 0:
        errors.append("模板名称不能为空")
    
    if request.category not in TEMPLATE_CATEGORIES:
        warnings.append(f"分类 '{request.category}' 不在推荐分类列表中")
    
    # 结构验证
    if request.structure:
        if not isinstance(request.structure, dict):
            errors.append("结构定义必须是JSON对象")
        else:
            # 检查sections字段
            if "sections" in request.structure:
                sections = request.structure["sections"]
                if not isinstance(sections, list) or len(sections) == 0:
                    errors.append("sections必须是非空数组")
                elif len(sections) > 20:
                    warnings.append("sections数量过多，建议控制在20个以内")
    
    # 提示模板验证
    if request.prompt_template:
        if len(request.prompt_template) < 20:
            warnings.append("提示模板内容较短，可能影响AI处理效果")
        elif len(request.prompt_template) > 2000:
            errors.append("提示模板内容过长，请控制在2000字符以内")
    
    is_valid = len(errors) == 0
    
    return {
        "success": True,
        "data": {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }
    }