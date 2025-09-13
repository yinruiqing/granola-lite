'use client';

import { useState, useRef, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Search, 
  X, 
  Clock, 
  Zap, 
  TrendingUp, 
  History,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  onSearch: (query: string) => void;
  placeholder?: string;
  suggestions?: string[];
  searchHistory?: string[];
  loading?: boolean;
  className?: string;
}

const popularSearches = [
  '项目会议',
  '周会',
  '需求讨论', 
  '技术分享',
  '一对一',
  '培训',
  '面试',
  'OKR'
];

const smartSuggestions = [
  { query: '今天的会议', description: '查看今日所有会议' },
  { query: '未完成的任务', description: '查找待办事项' },
  { query: '重要的决策', description: '找到关键决定' },
  { query: 'AI增强的笔记', description: '已优化的内容' }
];

export function SearchInput({
  value,
  onChange,
  onSearch,
  placeholder = "搜索会议、笔记、模板...",
  suggestions = [],
  searchHistory = [],
  loading = false,
  className
}: SearchInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedSuggestionIndex, setSelectedSuggestionIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionRefs = useRef<(HTMLDivElement | null)[]>([]);

  // 合并所有建议
  const allSuggestions = [
    ...suggestions.map(s => ({ type: 'suggestion', text: s })),
    ...searchHistory.slice(0, 5).map(h => ({ type: 'history', text: h }))
  ];

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    setShowSuggestions(true);
    setSelectedSuggestionIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (selectedSuggestionIndex >= 0 && selectedSuggestionIndex < allSuggestions.length) {
        const selectedSuggestion = allSuggestions[selectedSuggestionIndex].text;
        onChange(selectedSuggestion);
        onSearch(selectedSuggestion);
      } else {
        onSearch(value);
      }
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
      inputRef.current?.blur();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => 
        prev < allSuggestions.length - 1 ? prev + 1 : prev
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedSuggestionIndex(prev => prev > 0 ? prev - 1 : -1);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
      inputRef.current?.blur();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    onChange(suggestion);
    onSearch(suggestion);
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
    inputRef.current?.focus();
  };

  const handleClearSearch = () => {
    onChange('');
    setShowSuggestions(false);
    setSelectedSuggestionIndex(-1);
    inputRef.current?.focus();
  };

  const handleFocus = () => {
    setIsFocused(true);
    setShowSuggestions(true);
  };

  const handleBlur = () => {
    setIsFocused(false);
    // 延迟隐藏建议，以便点击建议时能够触发
    setTimeout(() => {
      setShowSuggestions(false);
      setSelectedSuggestionIndex(-1);
    }, 200);
  };

  // 滚动到选中的建议
  useEffect(() => {
    if (selectedSuggestionIndex >= 0 && suggestionRefs.current[selectedSuggestionIndex]) {
      suggestionRefs.current[selectedSuggestionIndex]?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest'
      });
    }
  }, [selectedSuggestionIndex]);

  return (
    <div className={cn("relative", className)}>
      {/* 搜索输入框 */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          {loading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
          ) : (
            <Search className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
        
        <Input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          className={cn(
            "pl-10 pr-10 py-3 text-base",
            isFocused && "ring-2 ring-primary ring-opacity-20"
          )}
        />
        
        {value && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearSearch}
              className="h-6 w-6 p-0 hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      {/* 建议下拉框 */}
      {showSuggestions && (
        <Card className="absolute top-full left-0 right-0 mt-1 z-50 shadow-lg border">
          <div className="max-h-96 overflow-hidden">
            <ScrollArea className="max-h-96">
              <div className="p-2">
                {/* 输入建议 */}
                {allSuggestions.length > 0 && (
                  <div className="space-y-1">
                    {allSuggestions.map((item, index) => (
                      <div
                        key={`${item.type}-${item.text}-${index}`}
                        ref={el => suggestionRefs.current[index] = el}
                        onClick={() => handleSuggestionClick(item.text)}
                        className={cn(
                          "flex items-center space-x-3 px-3 py-2 rounded-md cursor-pointer transition-colors",
                          selectedSuggestionIndex === index 
                            ? "bg-primary text-primary-foreground" 
                            : "hover:bg-accent"
                        )}
                      >
                        <div className="flex-shrink-0">
                          {item.type === 'history' ? (
                            <Clock className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <Search className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                        <span className="flex-1 text-sm">{item.text}</span>
                        <ArrowRight className="h-3 w-3 opacity-50" />
                      </div>
                    ))}
                  </div>
                )}

                {/* 空状态下显示的内容 */}
                {allSuggestions.length === 0 && value.length === 0 && (
                  <div className="space-y-4 p-2">
                    {/* 热门搜索 */}
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <TrendingUp className="h-4 w-4 text-primary" />
                        <h4 className="text-sm font-medium">热门搜索</h4>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {popularSearches.map((search) => (
                          <Badge
                            key={search}
                            variant="secondary"
                            className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-colors"
                            onClick={() => handleSuggestionClick(search)}
                          >
                            {search}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <Separator />

                    {/* 智能建议 */}
                    <div>
                      <div className="flex items-center space-x-2 mb-3">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <h4 className="text-sm font-medium">智能建议</h4>
                      </div>
                      <div className="space-y-2">
                        {smartSuggestions.map((suggestion) => (
                          <div
                            key={suggestion.query}
                            onClick={() => handleSuggestionClick(suggestion.query)}
                            className="flex items-center justify-between p-2 rounded-md cursor-pointer hover:bg-accent transition-colors"
                          >
                            <div>
                              <div className="font-medium text-sm">{suggestion.query}</div>
                              <div className="text-xs text-muted-foreground">
                                {suggestion.description}
                              </div>
                            </div>
                            <Zap className="h-3 w-3 text-primary" />
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 搜索历史 */}
                    {searchHistory.length > 0 && (
                      <>
                        <Separator />
                        <div>
                          <div className="flex items-center space-x-2 mb-3">
                            <History className="h-4 w-4 text-primary" />
                            <h4 className="text-sm font-medium">搜索历史</h4>
                          </div>
                          <div className="space-y-1">
                            {searchHistory.slice(0, 5).map((query, index) => (
                              <div
                                key={`history-${index}`}
                                onClick={() => handleSuggestionClick(query)}
                                className="flex items-center space-x-3 px-2 py-1 rounded-md cursor-pointer hover:bg-accent transition-colors"
                              >
                                <Clock className="h-3 w-3 text-muted-foreground" />
                                <span className="text-sm">{query}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* 无建议时的提示 */}
                {allSuggestions.length === 0 && value.length > 0 && (
                  <div className="p-4 text-center text-muted-foreground">
                    <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">按 Enter 键搜索 "{value}"</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </Card>
      )}
    </div>
  );
}