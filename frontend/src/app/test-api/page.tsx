'use client';

import { useState, useEffect } from 'react';

interface Meeting {
  id: number;
  title: string;
  description?: string;
  status: string;
  template_id?: number;
  created_at: string;
  updated_at: string;
}

interface Template {
  id: number;
  name: string;
  description?: string;
  category?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export default function TestApiPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE_URL = 'http://localhost:8000/api/v1';

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // 获取模板
      const templatesResponse = await fetch(`${API_BASE_URL}/templates`);
      if (!templatesResponse.ok) {
        throw new Error(`Templates API error: ${templatesResponse.status}`);
      }
      const templatesData = await templatesResponse.json();
      setTemplates(templatesData);
      
      // 获取会议
      const meetingsResponse = await fetch(`${API_BASE_URL}/meetings`);
      if (!meetingsResponse.ok) {
        throw new Error(`Meetings API error: ${meetingsResponse.status}`);
      }
      const meetingsData = await meetingsResponse.json();
      setMeetings(meetingsData);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const createTestMeeting = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const meetingData = {
        title: `测试会议 - ${new Date().toLocaleString()}`,
        description: '通过前端创建的测试会议',
        template_id: templates.length > 0 ? templates[0].id : undefined
      };
      
      const response = await fetch(`${API_BASE_URL}/meetings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(meetingData)
      });
      
      if (!response.ok) {
        throw new Error(`Create meeting error: ${response.status}`);
      }
      
      const newMeeting = await response.json();
      setMeetings(prev => [newMeeting, ...prev]);
      
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-3xl font-bold mb-8">API 测试页面</h1>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          错误: {error}
        </div>
      )}
      
      <div className="flex gap-4 mb-6">
        <button
          onClick={fetchData}
          disabled={loading}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          {loading ? '加载中...' : '刷新数据'}
        </button>
        
        <button
          onClick={createTestMeeting}
          disabled={loading}
          className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
        >
          创建测试会议
        </button>
      </div>
      
      <div className="grid md:grid-cols-2 gap-6">
        {/* 模板列表 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">模板列表 ({templates.length})</h2>
          {templates.length > 0 ? (
            <div className="space-y-3">
              {templates.map((template) => (
                <div key={template.id} className="border p-3 rounded">
                  <h3 className="font-medium">{template.name}</h3>
                  <p className="text-sm text-gray-600">{template.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    分类: {template.category} | 
                    默认: {template.is_default ? '是' : '否'}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">暂无模板</p>
          )}
        </div>
        
        {/* 会议列表 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">会议列表 ({meetings.length})</h2>
          {meetings.length > 0 ? (
            <div className="space-y-3">
              {meetings.map((meeting) => (
                <div key={meeting.id} className="border p-3 rounded">
                  <h3 className="font-medium">{meeting.title}</h3>
                  <p className="text-sm text-gray-600">{meeting.description}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    状态: {meeting.status} | ID: {meeting.id}
                  </p>
                  <p className="text-xs text-gray-400">
                    创建时间: {new Date(meeting.created_at).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">暂无会议</p>
          )}
        </div>
      </div>
      
      {/* API 状态 */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">API 连接状态</h2>
        <div className="grid md:grid-cols-3 gap-4 text-sm">
          <div>
            <strong>后端地址:</strong><br />
            <code className="bg-gray-200 px-2 py-1 rounded text-xs">
              {API_BASE_URL}
            </code>
          </div>
          <div>
            <strong>前端地址:</strong><br />
            <code className="bg-gray-200 px-2 py-1 rounded text-xs">
              http://localhost:3000
            </code>
          </div>
          <div>
            <strong>连接状态:</strong><br />
            <span className={`px-2 py-1 rounded text-xs ${
              error ? 'bg-red-200 text-red-800' : 'bg-green-200 text-green-800'
            }`}>
              {error ? '连接错误' : '连接正常'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}