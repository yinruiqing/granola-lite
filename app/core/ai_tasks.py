"""
AI相关异步任务
"""

import asyncio
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.tasks import task, TaskPriority
from app.services.ai import ai_service_manager
from app.services.ai.base import AIProvider
from app.core.cache import cache_manager
from app.core.events import event_emitter, Events
from loguru import logger


@task(
    name='ai.transcribe_audio',
    queue='ai',
    priority=TaskPriority.HIGH,
    max_retries=3,
    time_limit=600,  # 10分钟
    soft_time_limit=540
)
def transcribe_audio_task(
    audio_data: bytes,
    filename: str,
    language: str = "auto",
    provider: str = None,
    user_id: int = None,
    meeting_id: int = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    异步音频转录任务
    
    Args:
        audio_data: 音频数据
        filename: 文件名
        language: 语言代码
        provider: AI提供商
        user_id: 用户ID
        meeting_id: 会议ID
        use_cache: 是否使用缓存
    
    Returns:
        转录结果字典
    """
    try:
        logger.info(f"开始转录音频: {filename} (用户: {user_id})")
        
        # 解析提供商
        ai_provider = None
        if provider:
            try:
                ai_provider = AIProvider(provider)
            except ValueError:
                logger.warning(f"无效的AI提供商: {provider}, 使用默认提供商")
        
        # 生成音频哈希用于缓存
        audio_hash = hashlib.md5(audio_data).hexdigest()
        
        # 检查缓存
        if use_cache:
            cache_key = f"transcription:{provider or 'default'}:{language}:{audio_hash}"
            cached_result = asyncio.run(cache_manager.get("ai_results", cache_key))
            if cached_result:
                logger.info(f"转录缓存命中: {cache_key}")
                return cached_result
        
        # 执行转录
        result = asyncio.run(ai_service_manager.transcribe_audio(
            audio_data=audio_data,
            provider=ai_provider,
            language=language,
            use_cache=use_cache
        ))
        
        # 构建返回结果
        transcription_result = {
            'text': result.text,
            'confidence': result.confidence,
            'language': result.language,
            'segments': result.segments,
            'speaker': result.speaker,
            'provider': provider or 'default',
            'filename': filename,
            'user_id': user_id,
            'meeting_id': meeting_id,
            'audio_hash': audio_hash,
            'created_at': datetime.now().isoformat()
        }
        
        # 缓存结果
        if use_cache:
            cache_key = f"transcription:{provider or 'default'}:{language}:{audio_hash}"
            asyncio.run(cache_manager.set(
                "ai_results", 
                cache_key, 
                transcription_result, 
                ttl=7200  # 2小时
            ))
        
        # 发射转录完成事件
        asyncio.run(event_emitter.emit(Events.AUDIO_TRANSCRIBED, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'filename': filename,
            'text_length': len(result.text),
            'provider': provider,
            'language': result.language
        }))
        
        logger.info(f"转录完成: {filename} ({len(result.text)} 字符)")
        
        return transcription_result
        
    except Exception as e:
        logger.error(f"音频转录失败: {e}")
        raise


@task(
    name='ai.enhance_notes',
    queue='ai',
    priority=TaskPriority.NORMAL,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240
)
def enhance_notes_task(
    original_notes: str,
    transcription: str,
    template_prompt: str = None,
    provider: str = None,
    user_id: int = None,
    meeting_id: int = None,
    note_id: int = None,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    异步笔记增强任务
    
    Args:
        original_notes: 原始笔记
        transcription: 转录内容
        template_prompt: 模板提示
        provider: AI提供商
        user_id: 用户ID
        meeting_id: 会议ID
        note_id: 笔记ID
        temperature: 温度参数
    
    Returns:
        增强后的笔记结果
    """
    try:
        logger.info(f"开始增强笔记 (用户: {user_id}, 笔记: {note_id})")
        
        # 解析提供商
        ai_provider = None
        if provider:
            try:
                ai_provider = AIProvider(provider)
            except ValueError:
                logger.warning(f"无效的AI提供商: {provider}, 使用默认提供商")
        
        # 生成内容哈希用于缓存
        content_data = f"{original_notes}:{transcription}:{template_prompt or ''}"
        content_hash = hashlib.md5(content_data.encode('utf-8')).hexdigest()
        
        # 检查缓存
        cache_key = f"enhancement:{provider or 'default'}:{content_hash}"
        cached_result = asyncio.run(cache_manager.get("ai_results", cache_key))
        if cached_result:
            logger.info(f"笔记增强缓存命中: {cache_key}")
            return cached_result
        
        # 获取LLM提供商实例
        if not ai_provider:
            ai_provider = list(ai_service_manager.llm_providers.keys())[0]
        
        if ai_provider not in ai_service_manager.llm_providers:
            raise ValueError(f"LLM提供商 {ai_provider.value} 不可用")
        
        llm_provider = ai_service_manager.llm_providers[ai_provider]
        
        # 执行笔记增强
        enhanced_notes = asyncio.run(llm_provider.enhance_notes(
            original_notes=original_notes,
            transcription=transcription,
            template_prompt=template_prompt,
            temperature=temperature
        ))
        
        # 构建返回结果
        enhancement_result = {
            'enhanced_notes': enhanced_notes,
            'original_notes': original_notes,
            'provider': provider or 'default',
            'user_id': user_id,
            'meeting_id': meeting_id,
            'note_id': note_id,
            'content_hash': content_hash,
            'template_used': template_prompt is not None,
            'created_at': datetime.now().isoformat()
        }
        
        # 缓存结果
        cache_key = f"enhancement:{provider or 'default'}:{content_hash}"
        asyncio.run(cache_manager.set(
            "ai_results",
            cache_key,
            enhancement_result,
            ttl=7200  # 2小时
        ))
        
        # 发射笔记增强完成事件
        asyncio.run(event_emitter.emit(Events.NOTE_AI_ENHANCED, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'note_id': note_id,
            'original_length': len(original_notes),
            'enhanced_length': len(enhanced_notes),
            'provider': provider
        }))
        
        logger.info(f"笔记增强完成 (笔记: {note_id})")
        
        return enhancement_result
        
    except Exception as e:
        logger.error(f"笔记增强失败: {e}")
        raise


@task(
    name='ai.answer_question',
    queue='ai',
    priority=TaskPriority.NORMAL,
    max_retries=2,
    time_limit=180,
    soft_time_limit=150
)
def answer_question_task(
    question: str,
    context: str,
    provider: str = None,
    user_id: int = None,
    meeting_id: int = None,
    temperature: float = 0.1
) -> Dict[str, Any]:
    """
    异步问答任务
    
    Args:
        question: 问题
        context: 上下文
        provider: AI提供商
        user_id: 用户ID
        meeting_id: 会议ID
        temperature: 温度参数
    
    Returns:
        问答结果
    """
    try:
        logger.info(f"开始回答问题 (用户: {user_id})")
        
        # 解析提供商
        ai_provider = None
        if provider:
            try:
                ai_provider = AIProvider(provider)
            except ValueError:
                logger.warning(f"无效的AI提供商: {provider}, 使用默认提供商")
        
        # 生成问答哈希用于缓存
        qa_data = f"{question}:{context[:1000]}"  # 限制上下文长度用于缓存键
        qa_hash = hashlib.md5(qa_data.encode('utf-8')).hexdigest()
        
        # 检查缓存
        cache_key = f"qa:{provider or 'default'}:{qa_hash}"
        cached_result = asyncio.run(cache_manager.get("ai_results", cache_key))
        if cached_result:
            logger.info(f"问答缓存命中: {cache_key}")
            return cached_result
        
        # 获取LLM提供商实例
        if not ai_provider:
            ai_provider = list(ai_service_manager.llm_providers.keys())[0]
        
        if ai_provider not in ai_service_manager.llm_providers:
            raise ValueError(f"LLM提供商 {ai_provider.value} 不可用")
        
        llm_provider = ai_service_manager.llm_providers[ai_provider]
        
        # 执行问答
        answer = asyncio.run(llm_provider.answer_question(
            question=question,
            context=context,
            temperature=temperature
        ))
        
        # 构建返回结果
        qa_result = {
            'question': question,
            'answer': answer,
            'context_length': len(context),
            'provider': provider or 'default',
            'user_id': user_id,
            'meeting_id': meeting_id,
            'qa_hash': qa_hash,
            'created_at': datetime.now().isoformat()
        }
        
        # 缓存结果
        cache_key = f"qa:{provider or 'default'}:{qa_hash}"
        asyncio.run(cache_manager.set(
            "ai_results",
            cache_key,
            qa_result,
            ttl=3600  # 1小时
        ))
        
        # 发射问答完成事件
        asyncio.run(event_emitter.emit(Events.AI_CHAT_MESSAGE, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'question': question,
            'answer_length': len(answer),
            'provider': provider
        }))
        
        logger.info(f"问答完成 (用户: {user_id})")
        
        return qa_result
        
    except Exception as e:
        logger.error(f"问答失败: {e}")
        raise


@task(
    name='ai.batch_transcribe',
    queue='ai',
    priority=TaskPriority.LOW,
    max_retries=2,
    time_limit=1800,  # 30分钟
    soft_time_limit=1680
)
def batch_transcribe_task(
    audio_files: list,
    language: str = "auto",
    provider: str = None,
    user_id: int = None,
    batch_id: str = None
) -> Dict[str, Any]:
    """
    批量音频转录任务
    
    Args:
        audio_files: 音频文件列表 [{'data': bytes, 'filename': str, 'meeting_id': int}]
        language: 语言代码
        provider: AI提供商
        user_id: 用户ID
        batch_id: 批次ID
    
    Returns:
        批量转录结果
    """
    try:
        logger.info(f"开始批量转录 (用户: {user_id}, 文件数: {len(audio_files)})")
        
        results = []
        failed_files = []
        
        for i, audio_file in enumerate(audio_files):
            try:
                # 执行单个转录任务
                result = transcribe_audio_task(
                    audio_data=audio_file['data'],
                    filename=audio_file['filename'],
                    language=language,
                    provider=provider,
                    user_id=user_id,
                    meeting_id=audio_file.get('meeting_id'),
                    use_cache=True
                )
                
                results.append({
                    'filename': audio_file['filename'],
                    'success': True,
                    'result': result
                })
                
                logger.info(f"批量转录进度: {i+1}/{len(audio_files)}")
                
            except Exception as e:
                logger.error(f"转录失败: {audio_file['filename']}: {e}")
                
                failed_files.append({
                    'filename': audio_file['filename'],
                    'error': str(e)
                })
                
                results.append({
                    'filename': audio_file['filename'],
                    'success': False,
                    'error': str(e)
                })
        
        # 构建批量结果
        batch_result = {
            'batch_id': batch_id,
            'user_id': user_id,
            'total_files': len(audio_files),
            'successful_files': len(audio_files) - len(failed_files),
            'failed_files': len(failed_files),
            'results': results,
            'failed_details': failed_files,
            'provider': provider,
            'language': language,
            'completed_at': datetime.now().isoformat()
        }
        
        logger.info(f"批量转录完成: 成功 {len(results) - len(failed_files)}, 失败 {len(failed_files)}")
        
        return batch_result
        
    except Exception as e:
        logger.error(f"批量转录失败: {e}")
        raise