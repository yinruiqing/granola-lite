"""
AI服务管理和监控API端点
"""

from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.db.database import get_db
from app.core.auth import require_current_user, require_admin_user, get_current_user
from app.services.ai.manager import ai_service_manager
from app.services.ai.base import AIProvider
from app.models.user import User
from loguru import logger


router = APIRouter()


class TranscriptionRequest(BaseModel):
    """转录请求模型"""
    language: Optional[str] = "auto"
    provider: Optional[str] = None
    use_cache: bool = True


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    use_cache: bool = True


class NotesEnhanceRequest(BaseModel):
    """笔记增强请求模型"""
    original_notes: str
    transcription: str
    template_prompt: Optional[str] = None
    provider: Optional[str] = None
    temperature: float = 0.3


class QuestionAnswerRequest(BaseModel):
    """问答请求模型"""
    question: str
    context: str
    provider: Optional[str] = None
    temperature: float = 0.1


@router.post("/transcribe", summary="语音转录")
async def transcribe_audio(
    file: UploadFile = File(...),
    request: TranscriptionRequest = Depends(),
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    上传音频文件进行转录
    
    - **file**: 音频文件
    - **language**: 语言代码 (auto, zh, en等)
    - **provider**: AI提供商 (可选)
    - **use_cache**: 是否使用缓存
    """
    try:
        # 验证文件类型
        allowed_types = [
            'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/aac',
            'audio/flac', 'audio/ogg', 'audio/webm'
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的音频格式: {file.content_type}"
            )
        
        # 验证文件大小 (最大100MB)
        content = await file.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="音频文件过大，最大支持100MB"
            )
        
        # 解析提供商
        provider = None
        if request.provider:
            try:
                provider = AIProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的AI提供商: {request.provider}"
                )
        
        # 执行转录
        result = await ai_service_manager.transcribe_audio(
            audio_data=content,
            provider=provider,
            language=request.language,
            use_cache=request.use_cache
        )
        
        logger.info(f"用户 {current_user.id} 转录音频成功: {file.filename}")
        
        return {
            "success": True,
            "result": {
                "text": result.text,
                "confidence": result.confidence,
                "language": result.language,
                "segments": result.segments,
                "speaker": result.speaker
            },
            "metadata": {
                "filename": file.filename,
                "content_type": file.content_type,
                "file_size": len(content)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="音频转录失败"
        )


@router.post("/chat-completion", summary="聊天完成")
async def chat_completion(
    request: ChatCompletionRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    大语言模型聊天完成
    
    - **messages**: 消息列表 [{"role": "user", "content": "..."}]
    - **model**: 模型名称 (可选)
    - **provider**: AI提供商 (可选)
    - **temperature**: 温度参数 (0-1)
    - **max_tokens**: 最大token数 (可选)
    - **use_cache**: 是否使用缓存
    """
    try:
        # 验证消息格式
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息列表不能为空"
            )
        
        for msg in request.messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="消息格式错误，需要包含role和content字段"
                )
            
            if msg["role"] not in ["system", "user", "assistant"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="消息角色必须是system、user或assistant"
                )
        
        # 解析提供商
        provider = None
        if request.provider:
            try:
                provider = AIProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的AI提供商: {request.provider}"
                )
        
        # 执行聊天完成
        result = await ai_service_manager.chat_completion(
            messages=request.messages,
            provider=provider,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            use_cache=request.use_cache
        )
        
        logger.info(f"用户 {current_user.id} 执行聊天完成成功")
        
        return {
            "success": True,
            "result": {
                "content": result.content,
                "model": result.model,
                "usage": result.usage,
                "finish_reason": result.finish_reason,
                "metadata": result.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天完成失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="聊天完成失败"
        )


@router.post("/enhance-notes", summary="增强笔记")
async def enhance_notes(
    request: NotesEnhanceRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    使用AI增强笔记内容
    
    - **original_notes**: 原始笔记
    - **transcription**: 转录内容
    - **template_prompt**: 模板提示 (可选)
    - **provider**: AI提供商 (可选)
    - **temperature**: 温度参数
    """
    try:
        if not request.original_notes.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="原始笔记不能为空"
            )
        
        if not request.transcription.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="转录内容不能为空"
            )
        
        # 解析提供商
        provider = None
        if request.provider:
            try:
                provider = AIProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的AI提供商: {request.provider}"
                )
        
        # 获取LLM提供商实例
        if not provider:
            provider = list(ai_service_manager.llm_providers.keys())[0]
        
        if provider not in ai_service_manager.llm_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM提供商 {provider.value} 不可用"
            )
        
        llm_provider = ai_service_manager.llm_providers[provider]
        
        # 执行笔记增强
        enhanced_notes = await llm_provider.enhance_notes(
            original_notes=request.original_notes,
            transcription=request.transcription,
            template_prompt=request.template_prompt,
            temperature=request.temperature
        )
        
        logger.info(f"用户 {current_user.id} 增强笔记成功")
        
        return {
            "success": True,
            "enhanced_notes": enhanced_notes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"笔记增强失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="笔记增强失败"
        )


@router.post("/answer-question", summary="基于内容问答")
async def answer_question(
    request: QuestionAnswerRequest,
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    基于会议内容回答问题
    
    - **question**: 问题
    - **context**: 上下文内容
    - **provider**: AI提供商 (可选)
    - **temperature**: 温度参数
    """
    try:
        if not request.question.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="问题不能为空"
            )
        
        if not request.context.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上下文内容不能为空"
            )
        
        # 解析提供商
        provider = None
        if request.provider:
            try:
                provider = AIProvider(request.provider)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的AI提供商: {request.provider}"
                )
        
        # 获取LLM提供商实例
        if not provider:
            provider = list(ai_service_manager.llm_providers.keys())[0]
        
        if provider not in ai_service_manager.llm_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"LLM提供商 {provider.value} 不可用"
            )
        
        llm_provider = ai_service_manager.llm_providers[provider]
        
        # 执行问答
        answer = await llm_provider.answer_question(
            question=request.question,
            context=request.context,
            temperature=request.temperature
        )
        
        logger.info(f"用户 {current_user.id} 问答成功")
        
        return {
            "success": True,
            "answer": answer,
            "question": request.question
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="问答失败"
        )


@router.get("/health", summary="获取AI服务健康状态")
async def get_ai_service_health(
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取AI服务健康状态
    """
    try:
        health_data = ai_service_manager.get_provider_health()
        
        return {
            "success": True,
            "health": {
                provider.value: {
                    "status": health.status.value,
                    "response_time": health.response_time,
                    "error_count": health.error_count,
                    "success_count": health.success_count,
                    "last_check": health.last_check.isoformat(),
                    "last_error": health.last_error
                }
                for provider, health in health_data.items()
            }
        }
        
    except Exception as e:
        logger.error(f"获取AI服务健康状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取健康状态失败"
        )


@router.get("/metrics", summary="获取AI服务指标")
async def get_ai_service_metrics(
    current_user: User = Depends(require_admin_user)
) -> Dict[str, Any]:
    """
    获取AI服务指标（需要管理员权限）
    """
    try:
        metrics = ai_service_manager.get_metrics()
        
        return {
            "success": True,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"获取AI服务指标失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取服务指标失败"
        )


@router.get("/providers", summary="获取可用的AI提供商")
async def get_available_providers(
    current_user: Optional[User] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前可用的AI提供商列表
    """
    try:
        return {
            "success": True,
            "providers": {
                "stt": [provider.value for provider in ai_service_manager.stt_providers.keys()],
                "llm": [provider.value for provider in ai_service_manager.llm_providers.keys()],
                "all_supported": [provider.value for provider in AIProvider]
            }
        }
        
    except Exception as e:
        logger.error(f"获取AI提供商列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取提供商列表失败"
        )