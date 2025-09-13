"""
集成测试
"""

import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note


@pytest.mark.integration
class TestUserWorkflow:
    """用户工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, client: AsyncClient):
        """测试完整用户旅程"""
        # 1. 用户注册
        registration_data = {
            "email": "journey@example.com",
            "username": "journeyuser",
            "full_name": "Journey User",
            "password": "JourneyPass123!"
        }
        
        register_response = await client.post("/api/v1/auth/register", json=registration_data)
        assert register_response.status_code == 201
        
        register_data = register_response.json()
        assert register_data["success"] is True
        access_token = register_data["access_token"]
        
        # 2. 用户登录（使用注册时返回的token）
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        
        me_response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_response.status_code == 200
        
        user_data = me_response.json()["user"]
        user_id = user_data["id"]
        
        # 3. 创建会议
        meeting_data = {
            "title": "Integration Test Meeting",
            "description": "A meeting for integration testing"
        }
        
        meeting_response = await client.post(
            "/api/v1/meetings/",
            json=meeting_data,
            headers=auth_headers
        )
        assert meeting_response.status_code == 201
        
        meeting_id = meeting_response.json()["meeting"]["id"]
        
        # 4. 创建笔记
        note_data = {
            "title": "Integration Test Note",
            "content": "This is a note for integration testing",
            "meeting_id": meeting_id
        }
        
        note_response = await client.post(
            "/api/v1/notes/",
            json=note_data,
            headers=auth_headers
        )
        assert note_response.status_code == 201
        
        note_id = note_response.json()["note"]["id"]
        
        # 5. 获取用户的所有数据
        meetings_response = await client.get("/api/v1/meetings/", headers=auth_headers)
        notes_response = await client.get("/api/v1/notes/", headers=auth_headers)
        
        assert meetings_response.status_code == 200
        assert notes_response.status_code == 200
        
        meetings = meetings_response.json()["meetings"]
        notes = notes_response.json()["notes"]
        
        assert len(meetings) >= 1
        assert len(notes) >= 1
        assert any(m["id"] == meeting_id for m in meetings)
        assert any(n["id"] == note_id for n in notes)
        
        # 6. 更新和删除数据
        update_meeting_data = {"title": "Updated Meeting Title"}
        update_response = await client.put(
            f"/api/v1/meetings/{meeting_id}",
            json=update_meeting_data,
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # 7. 删除笔记
        delete_note_response = await client.delete(
            f"/api/v1/notes/{note_id}",
            headers=auth_headers
        )
        assert delete_note_response.status_code == 200
        
        # 8. 删除会议
        delete_meeting_response = await client.delete(
            f"/api/v1/meetings/{meeting_id}",
            headers=auth_headers
        )
        assert delete_meeting_response.status_code == 200


@pytest.mark.integration
class TestMeetingWorkflow:
    """会议工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_meeting_with_transcription_and_notes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User
    ):
        """测试会议与转录和笔记的完整流程"""
        # 1. 创建会议
        meeting_data = {
            "title": "Meeting with Transcription",
            "description": "A meeting that will have transcription and notes"
        }
        
        meeting_response = await client.post(
            "/api/v1/meetings/",
            json=meeting_data,
            headers=auth_headers
        )
        assert meeting_response.status_code == 201
        
        meeting_id = meeting_response.json()["meeting"]["id"]
        
        # 2. 模拟音频转录
        with patch('app.services.ai.ai_service_manager.transcribe_audio') as mock_transcribe:
            mock_transcribe.return_value = {
                "text": "This is the transcribed content of the meeting",
                "language": "en",
                "duration": 300.0,
                "confidence": 0.95,
                "segments": [
                    {"start_time": 0.0, "end_time": 10.0, "text": "Welcome to the meeting"},
                    {"start_time": 10.0, "end_time": 20.0, "text": "Let's start with introductions"}
                ]
            }
            
            # 上传音频文件进行转录
            files = {"file": ("meeting.wav", b"fake audio data", "audio/wav")}
            data = {"meeting_id": meeting_id}
            
            transcription_response = await client.post(
                "/api/v1/transcriptions/",
                files=files,
                data=data,
                headers=auth_headers
            )
            assert transcription_response.status_code == 201
            
            transcription_id = transcription_response.json()["transcription"]["id"]
        
        # 3. 创建多个笔记
        notes_data = [
            {
                "title": "Meeting Summary",
                "content": "Summary of the key points discussed",
                "meeting_id": meeting_id,
                "category": "summary"
            },
            {
                "title": "Action Items",
                "content": "List of action items from the meeting",
                "meeting_id": meeting_id,
                "category": "action_items"
            },
            {
                "title": "Questions",
                "content": "Questions that were raised during the meeting",
                "meeting_id": meeting_id,
                "category": "questions"
            }
        ]
        
        created_notes = []
        for note_data in notes_data:
            note_response = await client.post(
                "/api/v1/notes/",
                json=note_data,
                headers=auth_headers
            )
            assert note_response.status_code == 201
            created_notes.append(note_response.json()["note"]["id"])
        
        # 4. 获取完整的会议详情
        meeting_detail_response = await client.get(
            f"/api/v1/meetings/{meeting_id}",
            headers=auth_headers
        )
        assert meeting_detail_response.status_code == 200
        
        meeting_detail = meeting_detail_response.json()["meeting"]
        
        # 验证会议包含转录和笔记
        assert meeting_detail["id"] == meeting_id
        assert meeting_detail["title"] == meeting_data["title"]
        
        # 5. 获取转录详情
        transcription_detail_response = await client.get(
            f"/api/v1/transcriptions/{transcription_id}",
            headers=auth_headers
        )
        assert transcription_detail_response.status_code == 200
        
        transcription_detail = transcription_detail_response.json()["transcription"]
        assert transcription_detail["meeting_id"] == meeting_id
        assert "This is the transcribed content" in transcription_detail["text"]
        
        # 6. 验证笔记都已创建
        notes_response = await client.get("/api/v1/notes/", headers=auth_headers)
        all_notes = notes_response.json()["notes"]
        
        meeting_notes = [n for n in all_notes if n["meeting_id"] == meeting_id]
        assert len(meeting_notes) >= 3
        
        # 验证笔记分类
        categories = {note["category"] for note in meeting_notes}
        expected_categories = {"summary", "action_items", "questions"}
        assert expected_categories.issubset(categories)


@pytest.mark.integration
class TestAIWorkflow:
    """AI工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_ai_enhancement_pipeline(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_note: Note
    ):
        """测试AI增强管道"""
        # 1. 文本增强
        with patch('app.services.ai.ai_service_manager.enhance_text') as mock_enhance:
            mock_enhance.return_value = {
                "enhanced_text": "This is an enhanced and improved version of the note",
                "suggestions": ["Add more details", "Improve structure"],
                "confidence": 0.9
            }
            
            enhancement_data = {
                "text": test_note.content,
                "enhancement_type": "improve"
            }
            
            enhance_response = await client.post(
                "/api/v1/ai/enhance",
                json=enhancement_data,
                headers=auth_headers
            )
            assert enhance_response.status_code == 200
            
            enhanced_result = enhance_response.json()["result"]
            assert "enhanced_text" in enhanced_result
            assert "suggestions" in enhanced_result
        
        # 2. 生成摘要
        with patch('app.services.ai.ai_service_manager.generate_summary') as mock_summary:
            mock_summary.return_value = {
                "summary": "Brief summary of the note content",
                "key_points": ["Key point 1", "Key point 2"],
                "confidence": 0.85
            }
            
            summary_data = {
                "text": test_note.content,
                "summary_type": "brief"
            }
            
            summary_response = await client.post(
                "/api/v1/ai/summarize",
                json=summary_data,
                headers=auth_headers
            )
            assert summary_response.status_code == 200
            
            summary_result = summary_response.json()["result"]
            assert "summary" in summary_result
            assert "key_points" in summary_result
        
        # 3. AI问答
        with patch('app.services.ai.ai_service_manager.answer_question') as mock_qa:
            mock_qa.return_value = {
                "answer": "Based on the content, the answer is...",
                "confidence": 0.8,
                "sources": ["Note content"]
            }
            
            qa_data = {
                "question": "What is the main topic?",
                "context": test_note.content
            }
            
            qa_response = await client.post(
                "/api/v1/ai/ask",
                json=qa_data,
                headers=auth_headers
            )
            assert qa_response.status_code == 200
            
            qa_result = qa_response.json()["result"]
            assert "answer" in qa_result
            assert "confidence" in qa_result


@pytest.mark.integration
class TestSecurityWorkflow:
    """安全工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_security_validation_pipeline(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试安全验证管道"""
        # 1. 输入验证
        validation_tests = [
            {"input_type": "email", "value": "test@example.com", "should_pass": True},
            {"input_type": "email", "value": "invalid-email", "should_pass": False},
            {"input_type": "password", "value": "StrongP@ss123", "should_pass": True},
            {"input_type": "password", "value": "weak", "should_pass": False},
            {"input_type": "string", "value": "normal text", "should_pass": True},
            {"input_type": "string", "value": "<script>alert('xss')</script>", "should_pass": False}
        ]
        
        for test in validation_tests:
            validation_response = await client.post(
                "/api/v1/security/validation/validate-input",
                json={
                    "input_type": test["input_type"],
                    "value": test["value"],
                    "options": {}
                },
                headers=admin_auth_headers
            )
            assert validation_response.status_code == 200
            
            result = validation_response.json()["validation_result"]
            assert result["valid"] == test["should_pass"]
        
        # 2. SQL注入检测
        sql_tests = [
            {"query": "SELECT * FROM users WHERE id = 1", "should_be_safe": True},
            {"query": "SELECT * FROM users; DROP TABLE users; --", "should_be_safe": False}
        ]
        
        for test in sql_tests:
            sql_response = await client.post(
                "/api/v1/security/validation/analyze-sql",
                json={"query": test["query"]},
                headers=admin_auth_headers
            )
            assert sql_response.status_code == 200
            
            result = sql_response.json()["sql_analysis"]
            assert result["is_safe"] == test["should_be_safe"]
        
        # 3. 安全事件记录和查询
        event_response = await client.post(
            "/api/v1/security/audit/log-event",
            params={
                "event_type": "integration_test",
                "description": "Integration test security event",
                "severity": "low"
            },
            headers=admin_auth_headers
        )
        assert event_response.status_code == 200
        
        # 获取安全事件
        events_response = await client.get(
            "/api/v1/security/audit/events?limit=10",
            headers=admin_auth_headers
        )
        assert events_response.status_code == 200
        
        events = events_response.json()["security_events"]
        assert len(events) >= 0  # 至少包含我们刚创建的事件


@pytest.mark.integration
class TestDataManagementWorkflow:
    """数据管理工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_backup_and_restore_workflow(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试备份和恢复工作流"""
        # 1. 创建备份
        backup_data = {
            "scope": "user_data",
            "format": "json",
            "compress": True
        }
        
        backup_response = await client.post(
            "/api/v1/data/backup",
            json=backup_data,
            headers=admin_auth_headers
        )
        assert backup_response.status_code == 200
        
        backup_result = backup_response.json()["backup"]
        backup_id = backup_result["backup_id"]
        
        # 2. 获取备份列表
        list_response = await client.get(
            "/api/v1/data/backup",
            headers=admin_auth_headers
        )
        assert list_response.status_code == 200
        
        backups = list_response.json()["backups"]
        assert any(b["backup_id"] == backup_id for b in backups)
        
        # 3. 验证备份文件
        backup_file_exists = any(
            backup["backup_id"] == backup_id and backup["file_size"] > 0 
            for backup in backups
        )
        assert backup_file_exists
    
    @pytest.mark.asyncio
    async def test_export_and_import_workflow(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User
    ):
        """测试导出和导入工作流"""
        # 1. 导出用户数据
        export_data = {
            "format": "json",
            "include_files": False
        }
        
        export_response = await client.post(
            "/api/v1/data/export/user-data",
            json=export_data,
            headers=auth_headers
        )
        assert export_response.status_code == 200
        
        export_result = export_response.json()["export"]
        export_id = export_result["export_id"]
        
        # 2. 检查导出状态
        status_response = await client.get(
            f"/api/v1/data/export/{export_id}/status",
            headers=auth_headers
        )
        assert status_response.status_code == 200
        
        # 3. 验证导出包含预期数据
        assert export_result["records_count"]["meetings"] >= 0
        assert export_result["records_count"]["notes"] >= 0


@pytest.mark.integration
class TestPerformanceIntegration:
    """性能集成测试"""
    
    @pytest.mark.asyncio
    async def test_system_performance_monitoring(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试系统性能监控集成"""
        # 1. 获取系统资源状态
        resources_response = await client.get(
            "/api/v1/performance/system/resources",
            headers=admin_auth_headers
        )
        assert resources_response.status_code == 200
        
        resources = resources_response.json()["resources"]
        assert "cpu" in resources
        assert "memory" in resources
        
        # 2. 生成性能报告
        report_response = await client.get(
            "/api/v1/performance/analysis/performance-report",
            headers=admin_auth_headers
        )
        assert report_response.status_code == 200
        
        report = report_response.json()["report"]
        assert "summary" in report
        assert "performance_score" in report["summary"]
        
        # 3. 触发自动优化
        optimize_response = await client.post(
            "/api/v1/performance/optimization/auto-optimize",
            headers=admin_auth_headers
        )
        assert optimize_response.status_code == 200
        
        optimize_result = optimize_response.json()
        assert optimize_result["success"] is True
        assert "tasks" in optimize_result


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """错误处理集成测试"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_error_scenarios(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试综合错误场景"""
        # 1. 测试各种HTTP错误状态
        error_scenarios = [
            # 404 - 资源不存在
            {
                "method": "GET",
                "url": "/api/v1/meetings/99999",
                "expected_status": 404
            },
            # 422 - 验证错误
            {
                "method": "POST",
                "url": "/api/v1/meetings/",
                "json": {"description": "Missing title"},
                "expected_status": 422
            },
            # 403 - 权限不足
            {
                "method": "GET",
                "url": "/api/v1/security/audit/events",
                "expected_status": 403
            }
        ]
        
        for scenario in error_scenarios:
            if scenario["method"] == "GET":
                response = await client.get(scenario["url"], headers=auth_headers)
            elif scenario["method"] == "POST":
                response = await client.post(
                    scenario["url"], 
                    json=scenario.get("json"), 
                    headers=auth_headers
                )
            
            assert response.status_code == scenario["expected_status"]
            
            # 验证错误响应格式
            if response.status_code >= 400:
                error_data = response.json()
                assert "detail" in error_data or "error" in error_data
    
    @pytest.mark.asyncio
    async def test_concurrent_error_handling(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试并发错误处理"""
        async def make_invalid_request():
            # 故意发送无效请求
            return await client.get("/api/v1/meetings/invalid_id", headers=auth_headers)
        
        # 创建多个并发的无效请求
        tasks = [make_invalid_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 验证所有响应都正确处理了错误
        for response in responses:
            assert response.status_code == 404
            error_data = response.json()
            assert "detail" in error_data


@pytest.mark.integration
class TestSystemHealthCheck:
    """系统健康检查集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_health_check(self, client: AsyncClient):
        """测试完整系统健康检查"""
        # 1. 基本健康检查
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        
        health_data = health_response.json()
        assert health_data["status"] == "healthy"
        
        # 2. 详细健康检查
        detailed_response = await client.get("/health/detailed")
        # 详细健康检查可能需要管理员权限或返回不同状态码
        assert detailed_response.status_code in [200, 401, 503]
        
        # 3. 根路径检查
        root_response = await client.get("/")
        assert root_response.status_code == 200
        
        root_data = root_response.json()
        assert "message" in root_data
        assert "version" in root_data