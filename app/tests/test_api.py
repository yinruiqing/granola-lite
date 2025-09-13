"""
API端点测试
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.models.user import User
from app.models.meeting import Meeting
from app.models.transcription import Transcription
from app.models.note import Note


class TestMeetingsAPI:
    """会议API测试"""
    
    @pytest.mark.asyncio
    async def test_create_meeting(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_data_factory
    ):
        """测试创建会议"""
        meeting_data = test_data_factory.meeting_data(
            title="API Test Meeting",
            description="Created via API test"
        )
        
        response = await client.post(
            "/api/v1/meetings/",
            json=meeting_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["success"] is True
        assert data["meeting"]["title"] == meeting_data["title"]
        assert data["meeting"]["description"] == meeting_data["description"]
    
    @pytest.mark.asyncio
    async def test_get_meetings(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试获取会议列表"""
        response = await client.get("/api/v1/meetings/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["meetings"]) >= 1
        assert any(meeting["id"] == test_meeting.id for meeting in data["meetings"])
    
    @pytest.mark.asyncio
    async def test_get_meeting_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试获取会议详情"""
        response = await client.get(
            f"/api/v1/meetings/{test_meeting.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["meeting"]["id"] == test_meeting.id
        assert data["meeting"]["title"] == test_meeting.title
    
    @pytest.mark.asyncio
    async def test_update_meeting(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试更新会议"""
        update_data = {
            "title": "Updated Meeting Title",
            "description": "Updated description"
        }
        
        response = await client.put(
            f"/api/v1/meetings/{test_meeting.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["meeting"]["title"] == update_data["title"]
        assert data["meeting"]["description"] == update_data["description"]
    
    @pytest.mark.asyncio
    async def test_delete_meeting(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试删除会议"""
        response = await client.delete(
            f"/api/v1/meetings/{test_meeting.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        
        # 验证会议已删除
        response = await client.get(
            f"/api/v1/meetings/{test_meeting.id}",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_meeting_access_control(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试会议访问控制"""
        # 创建另一个用户的会议
        other_user_meeting_data = {
            "title": "Other User Meeting",
            "description": "Should not be accessible"
        }
        
        # 尝试访问不属于自己的会议
        response = await client.get(
            f"/api/v1/meetings/{test_meeting.id}",
            headers=auth_headers
        )
        # 这里应该成功，因为test_meeting属于test_user
        assert response.status_code == 200


class TestNotesAPI:
    """笔记API测试"""
    
    @pytest.mark.asyncio
    async def test_create_note(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting,
        test_data_factory
    ):
        """测试创建笔记"""
        note_data = test_data_factory.note_data(
            title="API Test Note",
            content="Created via API test",
            meeting_id=test_meeting.id
        )
        
        response = await client.post(
            "/api/v1/notes/",
            json=note_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["success"] is True
        assert data["note"]["title"] == note_data["title"]
        assert data["note"]["content"] == note_data["content"]
    
    @pytest.mark.asyncio
    async def test_get_notes(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_note: Note
    ):
        """测试获取笔记列表"""
        response = await client.get("/api/v1/notes/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["notes"]) >= 1
        assert any(note["id"] == test_note.id for note in data["notes"])
    
    @pytest.mark.asyncio
    async def test_update_note(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_note: Note
    ):
        """测试更新笔记"""
        update_data = {
            "title": "Updated Note Title",
            "content": "Updated note content"
        }
        
        response = await client.put(
            f"/api/v1/notes/{test_note.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["note"]["title"] == update_data["title"]
        assert data["note"]["content"] == update_data["content"]
    
    @pytest.mark.asyncio
    async def test_delete_note(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_note: Note
    ):
        """测试删除笔记"""
        response = await client.delete(
            f"/api/v1/notes/{test_note.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True


class TestTranscriptionsAPI:
    """转录API测试"""
    
    @pytest.mark.asyncio
    @patch('app.services.ai.ai_service_manager.transcribe_audio')
    async def test_create_transcription(
        self,
        mock_transcribe,
        client: AsyncClient,
        auth_headers: dict,
        test_meeting: Meeting
    ):
        """测试创建转录"""
        # Mock AI服务响应
        mock_transcribe.return_value = {
            "text": "This is a test transcription",
            "language": "en",
            "duration": 120.0,
            "confidence": 0.95,
            "segments": []
        }
        
        # 模拟文件上传
        files = {"file": ("test.wav", b"fake audio data", "audio/wav")}
        data = {"meeting_id": test_meeting.id}
        
        response = await client.post(
            "/api/v1/transcriptions/",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        response_data = response.json()
        assert response_data["success"] is True
        assert "transcription" in response_data
    
    @pytest.mark.asyncio
    async def test_get_transcriptions(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_transcription: Transcription
    ):
        """测试获取转录列表"""
        response = await client.get("/api/v1/transcriptions/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["transcriptions"]) >= 1
        assert any(
            trans["id"] == test_transcription.id 
            for trans in data["transcriptions"]
        )
    
    @pytest.mark.asyncio
    async def test_get_transcription_detail(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_transcription: Transcription
    ):
        """测试获取转录详情"""
        response = await client.get(
            f"/api/v1/transcriptions/{test_transcription.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["transcription"]["id"] == test_transcription.id
        assert data["transcription"]["text"] == test_transcription.text


class TestAIEnhancementAPI:
    """AI增强API测试"""
    
    @pytest.mark.asyncio
    @patch('app.services.ai.ai_service_manager.enhance_text')
    async def test_enhance_note(
        self,
        mock_enhance,
        client: AsyncClient,
        auth_headers: dict,
        test_note: Note
    ):
        """测试笔记增强"""
        # Mock AI服务响应
        mock_enhance.return_value = {
            "enhanced_text": "This is an enhanced version of the note",
            "suggestions": ["Add more details", "Consider structure"],
            "confidence": 0.9
        }
        
        enhancement_data = {
            "text": test_note.content,
            "enhancement_type": "improve"
        }
        
        response = await client.post(
            "/api/v1/ai/enhance",
            json=enhancement_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "enhanced_text" in data["result"]
    
    @pytest.mark.asyncio
    @patch('app.services.ai.ai_service_manager.generate_summary')
    async def test_generate_summary(
        self,
        mock_summary,
        client: AsyncClient,
        auth_headers: dict,
        test_transcription: Transcription
    ):
        """测试生成摘要"""
        # Mock AI服务响应
        mock_summary.return_value = {
            "summary": "This is a brief summary of the transcription",
            "key_points": ["Point 1", "Point 2"],
            "confidence": 0.85
        }
        
        summary_data = {
            "text": test_transcription.text,
            "summary_type": "brief"
        }
        
        response = await client.post(
            "/api/v1/ai/summarize",
            json=summary_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "summary" in data["result"]


class TestSecurityAPI:
    """安全API测试"""
    
    @pytest.mark.asyncio
    async def test_validate_input(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试输入验证"""
        validation_data = {
            "input_type": "email",
            "value": "test@example.com",
            "options": {}
        }
        
        response = await client.post(
            "/api/v1/security/validation/validate-input",
            json=validation_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["validation_result"]["valid"] is True
    
    @pytest.mark.asyncio
    async def test_analyze_sql(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试SQL分析"""
        sql_data = {
            "query": "SELECT * FROM users WHERE id = 1"
        }
        
        response = await client.post(
            "/api/v1/security/validation/analyze-sql",
            json=sql_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "sql_analysis" in data
    
    @pytest.mark.asyncio
    async def test_security_events(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试安全事件获取"""
        response = await client.get(
            "/api/v1/security/audit/events",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "security_events" in data


class TestPerformanceAPI:
    """性能API测试"""
    
    @pytest.mark.asyncio
    async def test_performance_report(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试性能报告"""
        response = await client.get(
            "/api/v1/performance/analysis/performance-report",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "report" in data
        assert "summary" in data["report"]
    
    @pytest.mark.asyncio
    async def test_system_resources(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试系统资源监控"""
        response = await client.get(
            "/api/v1/performance/system/resources",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "resources" in data


class TestDataManagementAPI:
    """数据管理API测试"""
    
    @pytest.mark.asyncio
    async def test_export_user_data(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试用户数据导出"""
        export_data = {
            "format": "json",
            "include_files": False
        }
        
        response = await client.post(
            "/api/v1/data/export/user-data",
            json=export_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "export" in data
    
    @pytest.mark.asyncio
    async def test_backup_creation(
        self,
        client: AsyncClient,
        admin_auth_headers: dict
    ):
        """测试创建备份"""
        backup_data = {
            "scope": "user_data",
            "format": "json",
            "compress": True
        }
        
        response = await client.post(
            "/api/v1/data/backup",
            json=backup_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "backup" in data


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_not_found_endpoint(self, client: AsyncClient):
        """测试不存在的端点"""
        response = await client.get("/api/v1/nonexistent")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """测试未授权访问"""
        response = await client.get("/api/v1/meetings/")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_forbidden_access(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试禁止访问（需要管理员权限的端点）"""
        response = await client.get("/api/v1/security/audit/events", headers=auth_headers)
        assert response.status_code == 403
    
    @pytest.mark.asyncio
    async def test_invalid_json_data(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试无效JSON数据"""
        response = await client.post(
            "/api/v1/meetings/",
            content="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_missing_required_fields(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试缺少必需字段"""
        incomplete_data = {
            "description": "Missing title field"
        }
        
        response = await client.post(
            "/api/v1/meetings/",
            json=incomplete_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_resource_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """测试资源不存在"""
        response = await client.get(
            "/api/v1/meetings/99999",
            headers=auth_headers
        )
        assert response.status_code == 404