"""
模板相关的Pydantic模式
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class TemplateBase(BaseModel):
    """模板基础模式"""
    name: str = Field(..., description="模板名称", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="模板描述", max_length=1000)
    category: str = Field(..., description="模板分类", min_length=1, max_length=100)
    structure: Optional[Dict[str, Any]] = Field(None, description="模板结构定义")
    prompt_template: Optional[str] = Field(None, description="AI处理提示模板", max_length=2000)
    is_default: bool = Field(default=False, description="是否为默认模板")


class TemplateCreate(TemplateBase):
    """创建模板请求模式"""
    
    class Config:
        schema_extra = {
            "example": {
                "name": "技术讨论会议",
                "description": "适用于技术团队的讨论会议",
                "category": "technical",
                "structure": {
                    "sections": [
                        "技术问题讨论",
                        "解决方案分析",
                        "技术决策",
                        "行动项",
                        "下一步计划"
                    ]
                },
                "prompt_template": "请基于技术讨论会议内容，整理出结构化的会议纪要，重点突出技术决策和行动项。",
                "is_default": False
            }
        }


class TemplateUpdate(BaseModel):
    """更新模板请求模式"""
    name: Optional[str] = Field(None, description="模板名称", min_length=1, max_length=255)
    description: Optional[str] = Field(None, description="模板描述", max_length=1000)
    category: Optional[str] = Field(None, description="模板分类", min_length=1, max_length=100)
    structure: Optional[Dict[str, Any]] = Field(None, description="模板结构定义")
    prompt_template: Optional[str] = Field(None, description="AI处理提示模板", max_length=2000)
    is_default: Optional[bool] = Field(None, description="是否为默认模板")


class TemplateResponse(TemplateBase):
    """模板响应模式"""
    id: int = Field(..., description="模板ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """模板列表响应模式"""
    templates: List[TemplateResponse] = Field(..., description="模板列表")
    total: int = Field(..., description="总数量")
    limit: int = Field(..., description="限制数量")
    offset: int = Field(..., description="偏移量")
    has_more: bool = Field(..., description="是否还有更多数据")


class TemplateQuery(BaseModel):
    """模板查询参数"""
    category: Optional[str] = Field(None, description="分类筛选")
    is_default: Optional[bool] = Field(None, description="默认状态筛选")
    limit: int = Field(default=50, description="返回数量限制", ge=1, le=200)
    offset: int = Field(default=0, description="偏移量", ge=0)


class TemplateCategoryResponse(BaseModel):
    """模板分类响应模式"""
    category: str = Field(..., description="分类名称")
    total_templates: int = Field(..., description="该分类下的模板总数")
    default_templates: int = Field(..., description="该分类下的默认模板数")


class TemplateCategoriesResponse(BaseModel):
    """模板分类列表响应模式"""
    categories: List[TemplateCategoryResponse] = Field(..., description="分类列表")
    total_categories: int = Field(..., description="总分类数")


class TemplateDuplicateRequest(BaseModel):
    """模板复制请求模式"""
    new_name: Optional[str] = Field(None, description="新模板名称，不提供则自动生成")
    
    class Config:
        schema_extra = {
            "example": {
                "new_name": "我的自定义技术会议模板"
            }
        }


class TemplateValidationResponse(BaseModel):
    """模板验证响应模式"""
    is_valid: bool = Field(..., description="是否有效")
    errors: List[str] = Field(..., description="错误信息列表")
    warnings: List[str] = Field(..., description="警告信息列表")


class TemplateUsageStatsResponse(BaseModel):
    """模板使用统计响应模式"""
    template_id: int = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    total_meetings: int = Field(..., description="使用该模板的会议总数")
    recent_meetings: int = Field(..., description="最近30天使用次数")
    last_used: Optional[datetime] = Field(None, description="最后使用时间")


class TemplateStructureSchema(BaseModel):
    """模板结构模式定义"""
    sections: List[str] = Field(..., description="章节列表", min_items=1)
    required_fields: Optional[List[str]] = Field(None, description="必填字段")
    optional_fields: Optional[List[str]] = Field(None, description="可选字段")
    formatting_rules: Optional[Dict[str, str]] = Field(None, description="格式化规则")
    
    class Config:
        schema_extra = {
            "example": {
                "sections": [
                    "会议目标",
                    "讨论要点",
                    "决策事项",
                    "行动项",
                    "后续安排"
                ],
                "required_fields": ["会议目标", "行动项"],
                "optional_fields": ["参会人员", "资料链接"],
                "formatting_rules": {
                    "行动项": "使用 - [ ] 格式的清单",
                    "决策事项": "明确责任人和时间节点"
                }
            }
        }


# 预定义的模板分类
TEMPLATE_CATEGORIES = [
    "1on1",          # 一对一会议
    "retrospective", # 回顾会议
    "interview",     # 面试会议
    "sales",         # 销售会议
    "project",       # 项目讨论
    "technical",     # 技术会议
    "standup",       # 站会
    "planning",      # 规划会议
    "review",        # 评审会议
    "general"        # 通用会议
]


class TemplateImportRequest(BaseModel):
    """模板导入请求模式"""
    templates: List[TemplateCreate] = Field(..., description="要导入的模板列表", min_items=1)
    overwrite_existing: bool = Field(default=False, description="是否覆盖现有同名模板")


class TemplateImportResponse(BaseModel):
    """模板导入响应模式"""
    total_imported: int = Field(..., description="成功导入数量")
    total_skipped: int = Field(..., description="跳过数量")
    total_failed: int = Field(..., description="失败数量")
    imported_templates: List[TemplateResponse] = Field(..., description="成功导入的模板")
    skipped_templates: List[str] = Field(..., description="跳过的模板名称")
    failed_templates: List[Dict[str, str]] = Field(..., description="失败的模板及错误信息")


class TemplateExportResponse(BaseModel):
    """模板导出响应模式"""
    templates: List[TemplateResponse] = Field(..., description="导出的模板列表")
    exported_at: datetime = Field(..., description="导出时间")
    total_count: int = Field(..., description="导出数量")