"""
数据库初始化
"""

from sqlalchemy.ext.asyncio import AsyncEngine
import asyncio
import json

from app.db.base import Base
from app.db.session import engine
from app.models import Template


async def create_tables(engine: AsyncEngine):
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_default_templates():
    """初始化默认模板"""
    from app.db.session import AsyncSessionLocal
    
    default_templates = [
        {
            "name": "一对一会议",
            "description": "适用于一对一会议的记录模板",
            "category": "1on1",
            "structure": {
                "sections": [
                    "本周工作回顾",
                    "遇到的问题和挑战",
                    "下周工作计划",
                    "需要的支持",
                    "其他讨论"
                ]
            },
            "prompt_template": "请基于一对一会议的内容，整理出结构化的会议纪要，包括：工作回顾、问题挑战、计划安排、需要支持等方面。",
            "is_default": True
        },
        {
            "name": "团队回顾会议",
            "description": "适用于团队Sprint回顾会议",
            "category": "retrospective",
            "structure": {
                "sections": [
                    "做得好的地方",
                    "需要改进的地方",
                    "行动项",
                    "下一步计划"
                ]
            },
            "prompt_template": "请基于团队回顾会议内容，总结团队的优点、改进点、具体行动项和下一步计划。",
            "is_default": True
        },
        {
            "name": "面试会议",
            "description": "适用于面试记录",
            "category": "interview",
            "structure": {
                "sections": [
                    "候选人基本信息",
                    "技术能力评估",
                    "项目经验讨论",
                    "综合评价",
                    "下一步建议"
                ]
            },
            "prompt_template": "请基于面试内容，整理候选人的技术能力、项目经验、综合表现和推荐结论。",
            "is_default": True
        },
        {
            "name": "销售会议",
            "description": "适用于销售拜访和客户会议",
            "category": "sales",
            "structure": {
                "sections": [
                    "客户需求分析",
                    "产品介绍要点",
                    "客户关注点",
                    "下一步跟进",
                    "成交可能性"
                ]
            },
            "prompt_template": "请基于销售会议内容，分析客户需求、关注点、跟进计划和成交可能性。",
            "is_default": True
        },
        {
            "name": "项目讨论",
            "description": "适用于项目规划和讨论会议",
            "category": "project",
            "structure": {
                "sections": [
                    "项目目标",
                    "讨论要点",
                    "决策事项",
                    "行动项分配",
                    "时间节点"
                ]
            },
            "prompt_template": "请基于项目会议内容，明确项目目标、关键决策、行动项分配和时间安排。",
            "is_default": True
        }
    ]
    
    async with AsyncSessionLocal() as session:
        # 检查是否已经存在默认模板
        existing_templates = await session.execute(
            "SELECT COUNT(*) FROM templates WHERE is_default = 1"
        )
        count = existing_templates.scalar()
        
        if count == 0:
            # 添加默认模板
            for template_data in default_templates:
                template = Template(**template_data)
                session.add(template)
            
            await session.commit()
            print(f"已初始化 {len(default_templates)} 个默认模板")
        else:
            print(f"默认模板已存在，跳过初始化")


async def init_database():
    """初始化数据库"""
    print("开始初始化数据库...")
    
    # 创建表
    await create_tables(engine)
    print("数据库表创建完成")
    
    # 初始化默认数据
    await init_default_templates()
    print("默认数据初始化完成")
    
    print("数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(init_database())