"""
转录相关的异步任务
"""

from celery import current_task
from app.core.celery_app import celery_app
from app.core.events import event_emitter, Events
from app.services.ai.ai_service import get_ai_service
from app.services.transcription import get_transcription_service
from app.services.audio import get_audio_service
from loguru import logger


@celery_app.task(bind=True, name='transcribe_audio')
def transcribe_audio_task(self, audio_file_id: int, meeting_id: int):
    """异步转录音频文件"""
    try:
        # 更新任务状态
        self.update_state(state='PROCESSING', meta={'progress': 0})
        
        # 获取服务
        audio_service = get_audio_service()
        transcription_service = get_transcription_service()
        ai_service = get_ai_service()
        
        # 获取音频文件信息
        audio_file = audio_service.get_audio_file(audio_file_id)
        if not audio_file:
            raise Exception(f"Audio file not found: {audio_file_id}")
        
        # 更新进度
        self.update_state(state='PROCESSING', meta={'progress': 20})
        
        # 执行转录
        transcription_result = ai_service.transcribe_audio(audio_file['file_path'])
        
        # 更新进度
        self.update_state(state='PROCESSING', meta={'progress': 80})
        
        # 保存转录结果
        transcription = transcription_service.create_transcription(
            meeting_id=meeting_id,
            audio_file_id=audio_file_id,
            content=transcription_result['text'],
            language=transcription_result.get('language', 'unknown'),
            confidence=transcription_result.get('confidence', 0.0)
        )
        
        # 发射事件
        event_emitter.emit(Events.AUDIO_TRANSCRIBED, {
            'meeting_id': meeting_id,
            'audio_file_id': audio_file_id,
            'transcription_id': transcription['id']
        })
        
        return {
            'success': True,
            'transcription_id': transcription['id'],
            'audio_file_id': audio_file_id,
            'meeting_id': meeting_id
        }
        
    except Exception as e:
        logger.error(f"Transcription task failed: {e}")
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise


@celery_app.task(bind=True, name='batch_transcribe')
def batch_transcribe_task(self, audio_file_ids: list, meeting_id: int):
    """批量转录音频文件"""
    results = []
    total_files = len(audio_file_ids)
    
    for i, audio_file_id in enumerate(audio_file_ids):
        try:
            # 更新进度
            progress = int((i / total_files) * 100)
            self.update_state(state='PROCESSING', meta={
                'progress': progress,
                'current_file': i + 1,
                'total_files': total_files
            })
            
            # 调用单个转录任务
            result = transcribe_audio_task.apply(args=[audio_file_id, meeting_id])
            results.append({
                'audio_file_id': audio_file_id,
                'success': True,
                'result': result.get()
            })
            
        except Exception as e:
            logger.error(f"Failed to transcribe audio {audio_file_id}: {e}")
            results.append({
                'audio_file_id': audio_file_id,
                'success': False,
                'error': str(e)
            })
    
    return {
        'success': True,
        'total_files': total_files,
        'successful': len([r for r in results if r['success']]),
        'failed': len([r for r in results if not r['success']]),
        'results': results
    }