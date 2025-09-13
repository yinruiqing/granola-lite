"""
会议模板服务
"""

from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from sqlalchemy import select, and_, or_

from app.models.template import Template
from app.db.session import AsyncSessionLocal


class TemplateService:
    """会议模板服务"""
    
    async def create_template(
        self,
        name: str,
        description: Optional[str] = None,
        category: str = "general",
        structure: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
        is_default: bool = False
    ) -> Dict[str, Any]:
        """
        创建会议模板
        
        Args:
            name: 模板名称
            description: 模板描述
            category: 模板分类
            structure: 模板结构定义
            prompt_template: AI处理提示模板
            is_default: 是否为默认模板
            
        Returns:
            Dict[str, Any]: 创建的模板信息
        """
        try:
            async with AsyncSessionLocal() as session:
                # 检查名称是否重复
                existing = await session.execute(
                    select(Template).where(Template.name == name)
                )
                if existing.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="模板名称已存在")
                
                # 如果设置为默认模板，取消其他同类别的默认状态
                if is_default:
                    await session.execute(
                        select(Template).where(
                            and_(
                                Template.category == category,
                                Template.is_default == True
                            )
                        ).update({"is_default": False})
                    )
                
                # 创建模板
                template = Template(
                    name=name,
                    description=description,
                    category=category,
                    structure=structure or {},
                    prompt_template=prompt_template,
                    is_default=is_default
                )
                
                session.add(template)
                await session.commit()
                await session.refresh(template)
                
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "structure": template.structure,
                    "prompt_template": template.prompt_template,
                    "is_default": template.is_default,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"创建模板失败: {str(e)}"
            )
    
    async def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """获取单个模板"""
        try:
            async with AsyncSessionLocal() as session:
                template = await session.get(Template, template_id)
                
                if not template:
                    return None
                
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "structure": template.structure,
                    "prompt_template": template.prompt_template,
                    "is_default": template.is_default,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
                
        except Exception as e:
            print(f"获取模板失败: {e}")
            return None
    
    async def get_templates(
        self,
        category: Optional[str] = None,
        is_default: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        获取模板列表
        
        Args:
            category: 分类筛选
            is_default: 默认状态筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict[str, Any]: 模板列表和统计信息
        """
        try:
            async with AsyncSessionLocal() as session:
                query = select(Template)
                
                # 添加筛选条件
                conditions = []
                if category:
                    conditions.append(Template.category == category)
                if is_default is not None:
                    conditions.append(Template.is_default == is_default)
                
                if conditions:
                    query = query.where(and_(*conditions))
                
                # 获取总数
                count_query = select(Template.id).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = len(total_result.fetchall())
                
                # 分页查询
                query = query.order_by(Template.category, Template.name).limit(limit).offset(offset)
                result = await session.execute(query)
                templates = result.scalars().all()
                
                return {
                    "templates": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "description": t.description,
                            "category": t.category,
                            "structure": t.structure,
                            "prompt_template": t.prompt_template,
                            "is_default": t.is_default,
                            "created_at": t.created_at,
                            "updated_at": t.updated_at
                        }
                        for t in templates
                    ],
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + len(templates) < total
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取模板列表失败: {str(e)}"
            )
    
    async def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        structure: Optional[Dict[str, Any]] = None,
        prompt_template: Optional[str] = None,
        is_default: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """
        更新模板
        
        Args:
            template_id: 模板ID
            name: 新名称
            description: 新描述
            category: 新分类
            structure: 新结构
            prompt_template: 新提示模板
            is_default: 新默认状态
            
        Returns:
            Dict[str, Any]: 更新后的模板信息
        """
        try:
            async with AsyncSessionLocal() as session:
                template = await session.get(Template, template_id)
                
                if not template:
                    return None
                
                # 检查名称是否重复（如果要更新名称）
                if name and name != template.name:
                    existing = await session.execute(
                        select(Template).where(
                            and_(
                                Template.name == name,
                                Template.id != template_id
                            )
                        )
                    )
                    if existing.scalar_one_or_none():
                        raise HTTPException(status_code=400, detail="模板名称已存在")
                
                # 如果要设置为默认模板，取消同类别其他默认模板
                if is_default and (not template.is_default or category != template.category):
                    target_category = category or template.category
                    await session.execute(
                        select(Template).where(
                            and_(
                                Template.category == target_category,
                                Template.is_default == True,
                                Template.id != template_id
                            )
                        ).update({"is_default": False})
                    )
                
                # 更新字段
                if name is not None:
                    template.name = name
                if description is not None:
                    template.description = description
                if category is not None:
                    template.category = category
                if structure is not None:
                    template.structure = structure
                if prompt_template is not None:
                    template.prompt_template = prompt_template
                if is_default is not None:
                    template.is_default = is_default
                
                await session.commit()
                await session.refresh(template)
                
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "structure": template.structure,
                    "prompt_template": template.prompt_template,
                    "is_default": template.is_default,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
                
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"更新模板失败: {str(e)}"
            )
    
    async def delete_template(self, template_id: int) -> bool:
        """
        删除模板
        
        Args:
            template_id: 模板ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            async with AsyncSessionLocal() as session:
                template = await session.get(Template, template_id)
                
                if not template:
                    return False
                
                # 检查是否有会议在使用此模板
                from app.models.meeting import Meeting
                
                meetings_using_template = await session.execute(
                    select(Meeting.id).where(Meeting.template_id == template_id).limit(1)
                )
                
                if meetings_using_template.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400,
                        detail="无法删除模板，还有会议正在使用此模板"
                    )
                
                await session.delete(template)
                await session.commit()
                return True
                
        except HTTPException:
            raise
        except Exception as e:
            print(f"删除模板失败: {e}")
            return False
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """
        获取所有模板分类及统计信息
        
        Returns:
            List[Dict[str, Any]]: 分类列表
        """
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import func, distinct
                
                # 查询分类及每个分类的模板数量
                result = await session.execute(
                    select(
                        Template.category,
                        func.count(Template.id).label('count'),
                        func.sum(func.cast(Template.is_default, int)).label('default_count')
                    ).group_by(Template.category)
                )
                
                categories = []
                for row in result.fetchall():
                    categories.append({
                        "category": row.category,
                        "total_templates": row.count,
                        "default_templates": row.default_count or 0
                    })
                
                return categories
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"获取分类列表失败: {str(e)}"
            )
    
    async def get_default_template(self, category: str) -> Optional[Dict[str, Any]]:
        """
        获取指定分类的默认模板
        
        Args:
            category: 模板分类
            
        Returns:
            Dict[str, Any]: 默认模板信息
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(Template).where(
                        and_(
                            Template.category == category,
                            Template.is_default == True
                        )
                    )
                )
                
                template = result.scalar_one_or_none()
                
                if not template:
                    return None
                
                return {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                    "structure": template.structure,
                    "prompt_template": template.prompt_template,
                    "is_default": template.is_default,
                    "created_at": template.created_at,
                    "updated_at": template.updated_at
                }
                
        except Exception as e:
            print(f"获取默认模板失败: {e}")
            return None
    
    async def duplicate_template(
        self,
        template_id: int,
        new_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        复制模板
        
        Args:
            template_id: 源模板ID
            new_name: 新模板名称
            
        Returns:
            Dict[str, Any]: 新创建的模板信息
        """
        try:
            async with AsyncSessionLocal() as session:
                original_template = await session.get(Template, template_id)
                
                if not original_template:
                    return None
                
                # 生成新名称
                if not new_name:
                    new_name = f"{original_template.name} (副本)"
                
                # 检查名称冲突
                counter = 1
                base_name = new_name
                while True:
                    existing = await session.execute(
                        select(Template).where(Template.name == new_name)
                    )
                    if not existing.scalar_one_or_none():
                        break
                    counter += 1
                    new_name = f"{base_name} ({counter})"
                
                # 创建新模板
                new_template = Template(
                    name=new_name,
                    description=original_template.description,
                    category=original_template.category,
                    structure=original_template.structure,
                    prompt_template=original_template.prompt_template,
                    is_default=False  # 副本不设为默认
                )
                
                session.add(new_template)
                await session.commit()
                await session.refresh(new_template)
                
                return {
                    "id": new_template.id,
                    "name": new_template.name,
                    "description": new_template.description,
                    "category": new_template.category,
                    "structure": new_template.structure,
                    "prompt_template": new_template.prompt_template,
                    "is_default": new_template.is_default,
                    "created_at": new_template.created_at,
                    "updated_at": new_template.updated_at
                }
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"复制模板失败: {str(e)}"
            )


# 全局服务实例
template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """获取模板服务实例"""
    global template_service
    if template_service is None:
        template_service = TemplateService()
    return template_service