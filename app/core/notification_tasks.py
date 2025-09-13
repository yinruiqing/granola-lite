"""
通知相关异步任务
"""

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.tasks import task, TaskPriority
from app.config import settings
from app.core.events import event_emitter, Events
from loguru import logger


@task(
    name='notification.send_email',
    queue='notification',
    priority=TaskPriority.NORMAL,
    max_retries=3,
    time_limit=60,
    soft_time_limit=45
)
def send_email_task(
    to_email: str,
    subject: str,
    body: str,
    html_body: str = None,
    attachments: List[Dict[str, Any]] = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    发送邮件任务
    
    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        body: 邮件正文（纯文本）
        html_body: HTML邮件正文
        attachments: 附件列表 [{'filename': str, 'content': bytes, 'content_type': str}]
        user_id: 用户ID
    
    Returns:
        发送结果
    """
    try:
        logger.info(f"开始发送邮件: {subject} -> {to_email}")
        
        # 检查邮件配置
        if not hasattr(settings, 'smtp_host') or not settings.smtp_host:
            raise ValueError("SMTP服务器未配置")
        
        # 创建邮件消息
        msg = MIMEMultipart('alternative')
        msg['From'] = getattr(settings, 'smtp_from_email', 'noreply@granola.com')
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # 添加纯文本内容
        if body:
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
        
        # 添加HTML内容
        if html_body:
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
        
        # 添加附件
        if attachments:
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment["filename"]}'
                )
                msg.attach(part)
        
        # 连接SMTP服务器并发送邮件
        smtp_host = getattr(settings, 'smtp_host', 'localhost')
        smtp_port = getattr(settings, 'smtp_port', 587)
        smtp_username = getattr(settings, 'smtp_username', '')
        smtp_password = getattr(settings, 'smtp_password', '')
        smtp_use_tls = getattr(settings, 'smtp_use_tls', True)
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_use_tls:
                server.starttls()
            
            if smtp_username and smtp_password:
                server.login(smtp_username, smtp_password)
            
            server.send_message(msg)
        
        result = {
            'to_email': to_email,
            'subject': subject,
            'body_length': len(body) if body else 0,
            'html_body_length': len(html_body) if html_body else 0,
            'attachments_count': len(attachments) if attachments else 0,
            'user_id': user_id,
            'sent_at': datetime.now().isoformat(),
            'success': True
        }
        
        logger.info(f"邮件发送成功: {to_email}")
        
        return result
        
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        raise


@task(
    name='notification.send_batch_email',
    queue='notification',
    priority=TaskPriority.LOW,
    max_retries=2,
    time_limit=300,
    soft_time_limit=240
)
def send_batch_email_task(
    email_list: List[str],
    subject: str,
    body: str,
    html_body: str = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    批量发送邮件任务
    
    Args:
        email_list: 收件人邮箱列表
        subject: 邮件主题
        body: 邮件正文
        html_body: HTML邮件正文
        user_id: 用户ID
    
    Returns:
        批量发送结果
    """
    try:
        logger.info(f"开始批量发送邮件: {len(email_list)} 个收件人")
        
        results = []
        successful_count = 0
        failed_count = 0
        
        for email in email_list:
            try:
                # 调用单个邮件发送任务
                result = send_email_task(
                    to_email=email,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                    user_id=user_id
                )
                
                results.append({
                    'email': email,
                    'success': True,
                    'result': result
                })
                successful_count += 1
                
            except Exception as e:
                logger.error(f"发送邮件失败 {email}: {e}")
                results.append({
                    'email': email,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        batch_result = {
            'total_emails': len(email_list),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'success_rate': successful_count / len(email_list) * 100,
            'results': results,
            'user_id': user_id,
            'sent_at': datetime.now().isoformat()
        }
        
        logger.info(f"批量邮件发送完成: 成功 {successful_count}, 失败 {failed_count}")
        
        return batch_result
        
    except Exception as e:
        logger.error(f"批量邮件发送失败: {e}")
        raise


@task(
    name='notification.send_meeting_reminder',
    queue='notification',
    priority=TaskPriority.HIGH,
    max_retries=3,
    time_limit=60,
    soft_time_limit=45
)
def send_meeting_reminder_task(
    user_email: str,
    meeting_title: str,
    meeting_time: str,
    meeting_id: int,
    user_id: int,
    reminder_type: str = 'upcoming'
) -> Dict[str, Any]:
    """
    发送会议提醒任务
    
    Args:
        user_email: 用户邮箱
        meeting_title: 会议标题
        meeting_time: 会议时间
        meeting_id: 会议ID
        user_id: 用户ID
        reminder_type: 提醒类型 (upcoming, started, ended)
    
    Returns:
        发送结果
    """
    try:
        logger.info(f"发送会议提醒: {reminder_type} - {meeting_title}")
        
        # 根据提醒类型生成邮件内容
        subject_templates = {
            'upcoming': f"会议提醒: {meeting_title}",
            'started': f"会议开始: {meeting_title}",
            'ended': f"会议结束: {meeting_title}"
        }
        
        body_templates = {
            'upcoming': f"""
亲爱的用户，

您有一个即将开始的会议：

会议标题：{meeting_title}
会议时间：{meeting_time}

请准备好参加会议。

祝好，
Granola团队
""",
            'started': f"""
亲爱的用户，

您的会议已经开始：

会议标题：{meeting_title}
开始时间：{meeting_time}

请及时参加会议。

祝好，
Granola团队
""",
            'ended': f"""
亲爱的用户，

您的会议已经结束：

会议标题：{meeting_title}
结束时间：{meeting_time}

您可以查看会议笔记和转录内容。

祝好，
Granola团队
"""
        }
        
        subject = subject_templates.get(reminder_type, f"会议通知: {meeting_title}")
        body = body_templates.get(reminder_type, f"会议通知: {meeting_title}")
        
        # 发送邮件
        result = send_email_task(
            to_email=user_email,
            subject=subject,
            body=body,
            user_id=user_id
        )
        
        # 发射会议提醒事件
        asyncio.run(event_emitter.emit(Events.MEETING_REMINDER_SENT, {
            'user_id': user_id,
            'meeting_id': meeting_id,
            'reminder_type': reminder_type,
            'email': user_email
        }))
        
        result.update({
            'meeting_id': meeting_id,
            'reminder_type': reminder_type,
            'meeting_title': meeting_title
        })
        
        logger.info(f"会议提醒发送成功: {reminder_type}")
        
        return result
        
    except Exception as e:
        logger.error(f"会议提醒发送失败: {e}")
        raise


@task(
    name='notification.send_transcription_complete',
    queue='notification',
    priority=TaskPriority.NORMAL,
    max_retries=2,
    time_limit=60,
    soft_time_limit=45
)
def send_transcription_complete_task(
    user_email: str,
    filename: str,
    transcription_length: int,
    meeting_id: int = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    发送转录完成通知任务
    
    Args:
        user_email: 用户邮箱
        filename: 文件名
        transcription_length: 转录文本长度
        meeting_id: 会议ID
        user_id: 用户ID
    
    Returns:
        发送结果
    """
    try:
        logger.info(f"发送转录完成通知: {filename}")
        
        subject = f"转录完成: {filename}"
        body = f"""
亲爱的用户，

您的音频文件转录已完成：

文件名称：{filename}
转录长度：{transcription_length} 字符
完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

您可以登录系统查看完整的转录内容。

祝好，
Granola团队
"""
        
        # 发送邮件
        result = send_email_task(
            to_email=user_email,
            subject=subject,
            body=body,
            user_id=user_id
        )
        
        result.update({
            'filename': filename,
            'transcription_length': transcription_length,
            'meeting_id': meeting_id
        })
        
        logger.info(f"转录完成通知发送成功: {filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"转录完成通知发送失败: {e}")
        raise


@task(
    name='notification.send_system_alert',
    queue='notification',
    priority=TaskPriority.CRITICAL,
    max_retries=5,
    time_limit=30,
    soft_time_limit=20
)
def send_system_alert_task(
    alert_type: str,
    alert_message: str,
    severity: str = 'warning',
    additional_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    发送系统告警任务
    
    Args:
        alert_type: 告警类型
        alert_message: 告警消息
        severity: 严重程度 (info, warning, error, critical)
        additional_info: 附加信息
    
    Returns:
        发送结果
    """
    try:
        logger.info(f"发送系统告警: {alert_type} - {severity}")
        
        # 获取管理员邮箱列表
        admin_emails = getattr(settings, 'admin_emails', ['admin@granola.com'])
        
        subject = f"[{severity.upper()}] 系统告警: {alert_type}"
        body = f"""
系统告警通知

告警类型：{alert_type}
严重程度：{severity}
告警消息：{alert_message}
发生时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
        
        if additional_info:
            body += "附加信息：\n"
            for key, value in additional_info.items():
                body += f"  {key}: {value}\n"
        
        body += "\n请及时检查系统状态。\n\nGranola系统"
        
        # 发送给所有管理员
        results = []
        for admin_email in admin_emails:
            try:
                result = send_email_task(
                    to_email=admin_email,
                    subject=subject,
                    body=body
                )
                results.append({
                    'email': admin_email,
                    'success': True,
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"发送系统告警失败 {admin_email}: {e}")
                results.append({
                    'email': admin_email,
                    'success': False,
                    'error': str(e)
                })
        
        alert_result = {
            'alert_type': alert_type,
            'severity': severity,
            'message': alert_message,
            'admin_emails': admin_emails,
            'results': results,
            'sent_at': datetime.now().isoformat()
        }
        
        logger.info(f"系统告警发送完成: {alert_type}")
        
        return alert_result
        
    except Exception as e:
        logger.error(f"系统告警发送失败: {e}")
        raise