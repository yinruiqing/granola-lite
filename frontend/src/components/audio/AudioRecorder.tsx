'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Mic, MicOff, Square, Play, Pause, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface AudioRecorderProps {
  onAudioData?: (audioBlob: Blob) => void;
  onTranscriptionData?: (data: string) => void;
  meetingId?: number;
  autoTranscribe?: boolean;
}

type RecorderState = 'idle' | 'recording' | 'paused' | 'stopped';

export function AudioRecorder({ 
  onAudioData, 
  onTranscriptionData, 
  meetingId, 
  autoTranscribe = true 
}: AudioRecorderProps) {
  const [state, setState] = useState<RecorderState>('idle');
  const [duration, setDuration] = useState(0);
  const [audioLevel, setAudioLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const animationRef = useRef<number | null>(null);

  // 请求麦克风权限
  const requestPermission = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });
      
      streamRef.current = stream;
      setHasPermission(true);
      
      // 设置音频分析
      setupAudioAnalysis(stream);
      
      return stream;
    } catch (error) {
      console.error('获取麦克风权限失败:', error);
      setError('无法访问麦克风，请检查浏览器权限设置');
      setHasPermission(false);
      return null;
    }
  }, []);

  // 设置音频分析
  const setupAudioAnalysis = useCallback((stream: MediaStream) => {
    try {
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      source.connect(analyser);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      
      // 开始分析音频级别
      analyzeAudioLevel();
    } catch (error) {
      console.error('音频分析设置失败:', error);
    }
  }, []);

  // 分析音频级别
  const analyzeAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;
    
    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const analyze = () => {
      if (!analyserRef.current) return;
      
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      setAudioLevel(Math.min(100, (average / 255) * 100));
      
      if (state === 'recording') {
        animationRef.current = requestAnimationFrame(analyze);
      }
    };
    
    analyze();
  }, [state]);

  // 开始录音
  const startRecording = useCallback(async () => {
    try {
      let stream = streamRef.current;
      
      if (!stream) {
        stream = await requestPermission();
        if (!stream) return;
      }

      // 清空之前的录音数据
      audioChunksRef.current = [];
      
      // 创建 MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { 
          type: 'audio/webm;codecs=opus' 
        });
        onAudioData?.(audioBlob);
      };
      
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(1000); // 每秒收集数据
      
      setState('recording');
      setDuration(0);
      setError(null);
      
      // 开始计时
      intervalRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      
      // 开始音频级别分析
      analyzeAudioLevel();
      
    } catch (error) {
      console.error('开始录音失败:', error);
      setError('录音失败，请重试');
    }
  }, [requestPermission, onAudioData, analyzeAudioLevel]);

  // 暂停录音
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && state === 'recording') {
      mediaRecorderRef.current.pause();
      setState('paused');
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [state]);

  // 恢复录音
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && state === 'paused') {
      mediaRecorderRef.current.resume();
      setState('recording');
      
      // 恢复计时
      intervalRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
      
      // 恢复音频级别分析
      analyzeAudioLevel();
    }
  }, [state, analyzeAudioLevel]);

  // 停止录音
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    
    setState('stopped');
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    
    setAudioLevel(0);
  }, []);

  // 重置录音器
  const resetRecorder = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    
    audioChunksRef.current = [];
    setState('idle');
    setDuration(0);
    setAudioLevel(0);
    setError(null);
  }, []);

  // 格式化时间
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  // 初始化时请求权限
  useEffect(() => {
    if (typeof window !== 'undefined' && navigator.mediaDevices) {
      // 检查是否已有权限
      navigator.permissions?.query({ name: 'microphone' as PermissionName }).then(result => {
        setHasPermission(result.state === 'granted');
      }).catch(() => {
        // 如果权限API不支持，尝试直接请求
        setHasPermission(null);
      });
    } else {
      setError('您的浏览器不支持录音功能');
    }
  }, []);

  return (
    <Card className="w-full">
      <CardContent className="p-6">
        <div className="space-y-4">
          {/* 错误提示 */}
          {error && (
            <Alert>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* 录音状态显示 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Badge variant={state === 'recording' ? 'default' : 'secondary'}>
                {state === 'recording' && '🔴'} 
                {state === 'paused' && '⏸️'} 
                {state === 'stopped' && '⏹️'} 
                {state === 'idle' && '⚫'} 
                {state === 'idle' ? '就绪' : 
                 state === 'recording' ? '录音中' : 
                 state === 'paused' ? '已暂停' : '已停止'}
              </Badge>
              <span className="text-sm font-mono">{formatTime(duration)}</span>
            </div>

            {autoTranscribe && meetingId && (
              <Badge variant="outline">实时转录</Badge>
            )}
          </div>

          {/* 音频级别可视化 */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Volume2 className="h-4 w-4 text-muted-foreground" />
              <Progress value={audioLevel} className="flex-1" />
              <span className="text-xs text-muted-foreground w-8">
                {Math.round(audioLevel)}%
              </span>
            </div>
          </div>

          {/* 控制按钮 */}
          <div className="flex justify-center space-x-2">
            {state === 'idle' && (
              <>
                {hasPermission === false ? (
                  <Button onClick={requestPermission} variant="outline">
                    <Mic className="h-4 w-4 mr-2" />
                    授权麦克风
                  </Button>
                ) : (
                  <Button 
                    onClick={startRecording} 
                    disabled={hasPermission === false}
                    className="bg-red-500 hover:bg-red-600"
                  >
                    <Mic className="h-4 w-4 mr-2" />
                    开始录音
                  </Button>
                )}
              </>
            )}

            {state === 'recording' && (
              <>
                <Button onClick={pauseRecording} variant="outline">
                  <Pause className="h-4 w-4 mr-2" />
                  暂停
                </Button>
                <Button onClick={stopRecording}>
                  <Square className="h-4 w-4 mr-2" />
                  停止
                </Button>
              </>
            )}

            {state === 'paused' && (
              <>
                <Button onClick={resumeRecording} className="bg-green-500 hover:bg-green-600">
                  <Play className="h-4 w-4 mr-2" />
                  继续
                </Button>
                <Button onClick={stopRecording} variant="destructive">
                  <Square className="h-4 w-4 mr-2" />
                  停止
                </Button>
              </>
            )}

            {state === 'stopped' && (
              <Button onClick={resetRecorder}>
                <MicOff className="h-4 w-4 mr-2" />
                重新录音
              </Button>
            )}
          </div>

          {/* 录音提示 */}
          {state === 'recording' && (
            <div className="text-center text-sm text-muted-foreground">
              <p>正在录音中，请保持安静的环境以获得更好的转录效果</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}