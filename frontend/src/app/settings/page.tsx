'use client';

import { useState, useEffect } from 'react';
import { 
  Save,
  RefreshCw,
  Download,
  Upload,
  Eye,
  EyeOff,
  Check,
  X,
  AlertCircle,
  User,
  Bot,
  Mic,
  FileDown,
  Shield,
  Palette,
  Globe
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { settingsService } from '@/lib/settings-service';
import { UserSettings } from '@/types';

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<UserSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [validatingApi, setValidatingApi] = useState(false);
  const [apiValidationResult, setApiValidationResult] = useState<boolean | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importJson, setImportJson] = useState('');
  const [error, setError] = useState<string | null>(null);

  // 加载设置
  useEffect(() => {
    const loadSettings = () => {
      try {
        const userSettings = settingsService.getSettings();
        setSettings(userSettings);
        setOriginalSettings(JSON.parse(JSON.stringify(userSettings)));
      } catch (error) {
        console.error('加载设置失败:', error);
        setError('加载设置失败');
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  // 检查是否有变更
  useEffect(() => {
    if (settings && originalSettings) {
      setHasChanges(JSON.stringify(settings) !== JSON.stringify(originalSettings));
    }
  }, [settings, originalSettings]);

  // 更新设置
  const updateSetting = (key: string, value: any) => {
    if (!settings) return;

    const keys = key.split('.');
    const newSettings = JSON.parse(JSON.stringify(settings));
    
    let current = newSettings;
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;

    setSettings(newSettings);
    setError(null);
    
    // 如果是API相关设置变更，重置验证状态
    if (key.startsWith('ai.')) {
      setApiValidationResult(null);
    }
  };

  // 保存设置
  const handleSave = async () => {
    if (!settings) return;

    try {
      setSaving(true);
      settingsService.saveSettings(settings);
      setOriginalSettings(JSON.parse(JSON.stringify(settings)));
      setHasChanges(false);
      setError(null);
    } catch (error) {
      console.error('保存设置失败:', error);
      setError('保存设置失败');
    } finally {
      setSaving(false);
    }
  };

  // 重置设置
  const handleReset = () => {
    const confirmed = confirm('确定要重置所有设置吗？此操作不可撤销。');
    if (!confirmed) return;

    try {
      const defaultSettings = settingsService.resetSettings();
      setSettings(defaultSettings);
      setOriginalSettings(JSON.parse(JSON.stringify(defaultSettings)));
      setHasChanges(false);
      setApiValidationResult(null);
      setError(null);
    } catch (error) {
      console.error('重置设置失败:', error);
      setError('重置设置失败');
    }
  };

  // 验证API配置
  const handleValidateApi = async () => {
    if (!settings || !settings.ai.apiKey) {
      setError('请先输入API密钥');
      return;
    }

    try {
      setValidatingApi(true);
      setError(null);
      
      const isValid = await settingsService.validateApiConfig(
        settings.ai.provider,
        settings.ai.apiKey,
        settings.ai.baseUrl
      );
      
      setApiValidationResult(isValid);
      
      if (!isValid) {
        setError('API配置验证失败，请检查密钥和配置');
      }
    } catch (error) {
      console.error('API验证失败:', error);
      setApiValidationResult(false);
      setError('API验证过程中出现错误');
    } finally {
      setValidatingApi(false);
    }
  };

  // 导出设置
  const handleExportSettings = () => {
    try {
      const settingsJson = settingsService.exportSettings();
      const blob = new Blob([settingsJson], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `granola-settings-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('导出设置失败:', error);
      setError('导出设置失败');
    }
  };

  // 导入设置
  const handleImportSettings = () => {
    if (!importJson.trim()) {
      setError('请输入设置JSON');
      return;
    }

    try {
      const imported = settingsService.importSettings(importJson);
      setSettings(imported);
      setOriginalSettings(JSON.parse(JSON.stringify(imported)));
      setHasChanges(false);
      setShowImportDialog(false);
      setImportJson('');
      setApiValidationResult(null);
      setError(null);
    } catch (error) {
      console.error('导入设置失败:', error);
      setError('导入设置失败');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>加载设置中...</p>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h2 className="text-xl font-semibold mb-2">设置加载失败</h2>
        <p className="text-muted-foreground">请刷新页面重试</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">设置</h1>
          <p className="text-muted-foreground">
            自定义应用程序的行为和偏好设置
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleExportSettings}>
            <Download className="h-4 w-4 mr-2" />
            导出设置
          </Button>
          <Button variant="outline" onClick={() => setShowImportDialog(true)}>
            <Upload className="h-4 w-4 mr-2" />
            导入设置
          </Button>
          <Button variant="outline" onClick={handleReset}>
            <RefreshCw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button 
            onClick={handleSave}
            disabled={!hasChanges || saving}
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 未保存更改提示 */}
      {hasChanges && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-orange-600">
                <AlertCircle className="h-4 w-4" />
                <span>您有未保存的更改</span>
              </div>
              <Button onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? '保存中...' : '立即保存'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 设置选项卡 */}
      <Tabs defaultValue="general" className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="general">
            <User className="h-4 w-4 mr-2" />
            通用
          </TabsTrigger>
          <TabsTrigger value="ai">
            <Bot className="h-4 w-4 mr-2" />
            AI
          </TabsTrigger>
          <TabsTrigger value="transcription">
            <Mic className="h-4 w-4 mr-2" />
            转录
          </TabsTrigger>
          <TabsTrigger value="export">
            <FileDown className="h-4 w-4 mr-2" />
            导出
          </TabsTrigger>
          <TabsTrigger value="privacy">
            <Shield className="h-4 w-4 mr-2" />
            隐私
          </TabsTrigger>
          <TabsTrigger value="appearance">
            <Palette className="h-4 w-4 mr-2" />
            外观
          </TabsTrigger>
        </TabsList>

        {/* 通用设置 */}
        <TabsContent value="general">
          <Card>
            <CardHeader>
              <CardTitle>通用设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="language">语言</Label>
                  <Select
                    value={settings.language}
                    onValueChange={(value) => updateSetting('language', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {settingsService.getAvailableLanguages().map(lang => (
                        <SelectItem key={lang.value} value={lang.value}>
                          {lang.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone">时区</Label>
                  <Select
                    value={settings.timezone}
                    onValueChange={(value) => updateSetting('timezone', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {settingsService.getAvailableTimezones().map(tz => (
                        <SelectItem key={tz.value} value={tz.value}>
                          {tz.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h3 className="text-lg font-medium">会议设置</h3>
                
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label>默认会议时长（分钟）</Label>
                    <div className="space-y-3">
                      <Slider
                        value={[settings.defaultMeetingDuration]}
                        onValueChange={(value) => updateSetting('defaultMeetingDuration', value[0])}
                        min={15}
                        max={480}
                        step={15}
                        className="w-full"
                      />
                      <div className="text-sm text-muted-foreground">
                        当前值: {settings.defaultMeetingDuration} 分钟
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>自动保存间隔（秒）</Label>
                    <div className="space-y-3">
                      <Slider
                        value={[settings.autoSaveInterval]}
                        onValueChange={(value) => updateSetting('autoSaveInterval', value[0])}
                        min={10}
                        max={300}
                        step={10}
                        className="w-full"
                      />
                      <div className="text-sm text-muted-foreground">
                        当前值: {settings.autoSaveInterval} 秒
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label htmlFor="notifications">启用通知</Label>
                    <p className="text-sm text-muted-foreground">
                      接收会议提醒和系统通知
                    </p>
                  </div>
                  <Switch
                    id="notifications"
                    checked={settings.enableNotifications}
                    onCheckedChange={(checked) => updateSetting('enableNotifications', checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* AI 设置 */}
        <TabsContent value="ai">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                AI 配置
                {apiValidationResult !== null && (
                  <Badge variant={apiValidationResult ? "default" : "destructive"}>
                    {apiValidationResult ? (
                      <>
                        <Check className="h-3 w-3 mr-1" />
                        验证成功
                      </>
                    ) : (
                      <>
                        <X className="h-3 w-3 mr-1" />
                        验证失败
                      </>
                    )}
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>AI 提供商</Label>
                  <Select
                    value={settings.ai.provider}
                    onValueChange={(value) => updateSetting('ai.provider', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="claude">Claude</SelectItem>
                      <SelectItem value="local">本地模型</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>模型</Label>
                  <Select
                    value={settings.ai.model}
                    onValueChange={(value) => updateSetting('ai.model', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {settingsService.getAiModels(settings.ai.provider).map(model => (
                        <SelectItem key={model.value} value={model.value}>
                          {model.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {settings.ai.provider !== 'local' && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">API 密钥</Label>
                    <div className="flex space-x-2">
                      <div className="relative flex-1">
                        <Input
                          id="apiKey"
                          type={showApiKey ? 'text' : 'password'}
                          value={settings.ai.apiKey || ''}
                          onChange={(e) => updateSetting('ai.apiKey', e.target.value)}
                          placeholder="输入您的API密钥"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-2 top-1/2 -translate-y-1/2"
                          onClick={() => setShowApiKey(!showApiKey)}
                        >
                          {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      <Button
                        onClick={handleValidateApi}
                        disabled={validatingApi || !settings.ai.apiKey}
                      >
                        {validatingApi ? (
                          <RefreshCw className="h-4 w-4 animate-spin" />
                        ) : (
                          '验证'
                        )}
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="baseUrl">API 基础 URL（可选）</Label>
                    <Input
                      id="baseUrl"
                      value={settings.ai.baseUrl || ''}
                      onChange={(e) => updateSetting('ai.baseUrl', e.target.value)}
                      placeholder="https://api.openai.com/v1"
                    />
                  </div>
                </>
              )}

              <Separator />

              <div className="space-y-4">
                <h3 className="text-lg font-medium">模型参数</h3>
                
                <div className="space-y-2">
                  <Label>Temperature (创造性)</Label>
                  <div className="space-y-3">
                    <Slider
                      value={[settings.ai.temperature]}
                      onValueChange={(value) => updateSetting('ai.temperature', value[0])}
                      min={0}
                      max={1}
                      step={0.1}
                      className="w-full"
                    />
                    <div className="text-sm text-muted-foreground">
                      当前值: {settings.ai.temperature} (0 = 保守, 1 = 创造性)
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>最大令牌数</Label>
                  <div className="space-y-3">
                    <Slider
                      value={[settings.ai.maxTokens]}
                      onValueChange={(value) => updateSetting('ai.maxTokens', value[0])}
                      min={500}
                      max={4000}
                      step={100}
                      className="w-full"
                    />
                    <div className="text-sm text-muted-foreground">
                      当前值: {settings.ai.maxTokens} tokens
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 转录设置 */}
        <TabsContent value="transcription">
          <Card>
            <CardHeader>
              <CardTitle>转录设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>转录语言</Label>
                  <Select
                    value={settings.transcription.language}
                    onValueChange={(value) => updateSetting('transcription.language', value)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh-CN">中文（简体）</SelectItem>
                      <SelectItem value="zh-TW">中文（繁体）</SelectItem>
                      <SelectItem value="en-US">英语（美国）</SelectItem>
                      <SelectItem value="en-GB">英语（英国）</SelectItem>
                      <SelectItem value="ja-JP">日语</SelectItem>
                      <SelectItem value="ko-KR">韩语</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>自动检测语言</Label>
                    <p className="text-sm text-muted-foreground">
                      自动识别音频中的语言
                    </p>
                  </div>
                  <Switch
                    checked={settings.transcription.autoDetectLanguage}
                    onCheckedChange={(checked) => updateSetting('transcription.autoDetectLanguage', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>启用标点符号</Label>
                    <p className="text-sm text-muted-foreground">
                      在转录结果中添加标点符号
                    </p>
                  </div>
                  <Switch
                    checked={settings.transcription.enablePunctuation}
                    onCheckedChange={(checked) => updateSetting('transcription.enablePunctuation', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>启用内容过滤</Label>
                    <p className="text-sm text-muted-foreground">
                      过滤敏感内容和噪音
                    </p>
                  </div>
                  <Switch
                    checked={settings.transcription.enableFiltering}
                    onCheckedChange={(checked) => updateSetting('transcription.enableFiltering', checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 导出设置 */}
        <TabsContent value="export">
          <Card>
            <CardHeader>
              <CardTitle>导出设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>默认导出格式</Label>
                <Select
                  value={settings.export.defaultFormat}
                  onValueChange={(value) => updateSetting('export.defaultFormat', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="markdown">Markdown</SelectItem>
                    <SelectItem value="pdf">PDF</SelectItem>
                    <SelectItem value="docx">Word 文档</SelectItem>
                    <SelectItem value="txt">纯文本</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>包含时间戳</Label>
                    <p className="text-sm text-muted-foreground">
                      在导出的内容中包含时间信息
                    </p>
                  </div>
                  <Switch
                    checked={settings.export.includeTimestamps}
                    onCheckedChange={(checked) => updateSetting('export.includeTimestamps', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>包含元数据</Label>
                    <p className="text-sm text-muted-foreground">
                      在导出的内容中包含会议元信息
                    </p>
                  </div>
                  <Switch
                    checked={settings.export.includeMetadata}
                    onCheckedChange={(checked) => updateSetting('export.includeMetadata', checked)}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 隐私设置 */}
        <TabsContent value="privacy">
          <Card>
            <CardHeader>
              <CardTitle>隐私设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>启用使用分析</Label>
                    <p className="text-sm text-muted-foreground">
                      收集匿名使用数据以改善产品
                    </p>
                  </div>
                  <Switch
                    checked={settings.privacy.enableAnalytics}
                    onCheckedChange={(checked) => updateSetting('privacy.enableAnalytics', checked)}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <Label>启用崩溃报告</Label>
                    <p className="text-sm text-muted-foreground">
                      自动发送崩溃报告以帮助修复问题
                    </p>
                  </div>
                  <Switch
                    checked={settings.privacy.enableCrashReporting}
                    onCheckedChange={(checked) => updateSetting('privacy.enableCrashReporting', checked)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>数据保留期限（天）</Label>
                <div className="space-y-3">
                  <Slider
                    value={[settings.privacy.dataRetentionDays]}
                    onValueChange={(value) => updateSetting('privacy.dataRetentionDays', value[0])}
                    min={7}
                    max={365}
                    step={7}
                    className="w-full"
                  />
                  <div className="text-sm text-muted-foreground">
                    当前值: {settings.privacy.dataRetentionDays} 天
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 外观设置 */}
        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle>外观设置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>主题</Label>
                <Select
                  value={settings.theme}
                  onValueChange={(value) => updateSetting('theme', value)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">跟随系统</SelectItem>
                    <SelectItem value="light">浅色主题</SelectItem>
                    <SelectItem value="dark">深色主题</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* 导入设置对话框 */}
      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>导入设置</DialogTitle>
            <DialogDescription>
              粘贴导出的设置JSON文件内容
            </DialogDescription>
          </DialogHeader>

          <Textarea
            value={importJson}
            onChange={(e) => setImportJson(e.target.value)}
            placeholder="粘贴设置JSON..."
            rows={10}
            className="font-mono text-sm"
          />

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImportDialog(false)}>
              取消
            </Button>
            <Button onClick={handleImportSettings}>
              导入
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}