'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Filter, 
  Calendar as CalendarIcon, 
  Users, 
  Tags, 
  FileType, 
  X,
  RotateCcw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { SearchFilter } from '@/lib/search-service';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface SearchFiltersProps {
  filters: SearchFilter;
  onFiltersChange: (filters: SearchFilter) => void;
  availableData?: {
    participants: string[];
    categories: string[];
    types: string[];
    statuses: string[];
  };
  className?: string;
}

interface FilterSection {
  key: keyof SearchFilter;
  title: string;
  icon: React.ComponentType<any>;
  component: React.ReactNode;
}

export function SearchFilters({ 
  filters, 
  onFiltersChange, 
  availableData,
  className 
}: SearchFiltersProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['dateRange', 'status'])
  );
  const [tempDateRange, setTempDateRange] = useState<{
    start?: Date;
    end?: Date;
  }>({});

  // 默认可用数据
  const defaultAvailableData = {
    participants: ['张三', '李四', '王五', '赵六', '钱七'],
    categories: ['工作会议', '项目讨论', '培训学习', '团队建设', '一对一'],
    types: ['定期会议', '项目会议', '培训会议', '面试', '其他'],
    statuses: ['scheduled', 'in_progress', 'completed', 'cancelled'],
    ...availableData
  };

  const statusLabels: Record<string, string> = {
    scheduled: '已安排',
    in_progress: '进行中',
    completed: '已完成',
    cancelled: '已取消'
  };

  // 切换区域展开状态
  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(section)) {
        newSet.delete(section);
      } else {
        newSet.add(section);
      }
      return newSet;
    });
  };

  // 更新过滤器
  const updateFilters = (key: keyof SearchFilter, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  };

  // 重置所有过滤器
  const resetFilters = () => {
    onFiltersChange({});
    setTempDateRange({});
  };

  // 获取活跃过滤器数量
  const getActiveFiltersCount = () => {
    let count = 0;
    if (filters.dateRange) count++;
    if (filters.status?.length) count++;
    if (filters.participants?.length) count++;
    if (filters.categories?.length) count++;
    if (filters.types?.length) count++;
    if (filters.hasTranscription) count++;
    if (filters.hasNotes) count++;
    if (filters.hasAIEnhancement) count++;
    return count;
  };

  // 应用日期范围
  const applyDateRange = () => {
    if (tempDateRange.start && tempDateRange.end) {
      updateFilters('dateRange', {
        start: tempDateRange.start,
        end: tempDateRange.end
      });
    }
  };

  // 清除特定过滤器
  const clearFilter = (key: keyof SearchFilter) => {
    const newFilters = { ...filters };
    delete newFilters[key];
    onFiltersChange(newFilters);
    
    if (key === 'dateRange') {
      setTempDateRange({});
    }
  };

  const FilterSection: React.FC<{
    title: string;
    icon: React.ComponentType<any>;
    sectionKey: string;
    children: React.ReactNode;
    activeCount?: number;
  }> = ({ title, icon: Icon, sectionKey, children, activeCount }) => {
    const isExpanded = expandedSections.has(sectionKey);
    
    return (
      <div className="border rounded-lg">
        <div 
          className="flex items-center justify-between p-4 cursor-pointer hover:bg-accent/50 transition-colors"
          onClick={() => toggleSection(sectionKey)}
        >
          <div className="flex items-center space-x-2">
            <Icon className="h-4 w-4" />
            <span className="font-medium">{title}</span>
            {activeCount !== undefined && activeCount > 0 && (
              <Badge variant="secondary" className="ml-2">
                {activeCount}
              </Badge>
            )}
          </div>
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
        
        {isExpanded && (
          <div className="px-4 pb-4">
            <Separator className="mb-4" />
            {children}
          </div>
        )}
      </div>
    );
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>搜索过滤器</span>
          </CardTitle>
          <div className="flex items-center space-x-2">
            {getActiveFiltersCount() > 0 && (
              <Badge variant="outline">
                {getActiveFiltersCount()} 个活跃过滤器
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              disabled={getActiveFiltersCount() === 0}
            >
              <RotateCcw className="h-4 w-4 mr-1" />
              重置
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <ScrollArea className="max-h-[600px]">
          <div className="space-y-4">
            {/* 日期范围过滤 */}
            <FilterSection
              title="日期范围"
              icon={CalendarIcon}
              sectionKey="dateRange"
              activeCount={filters.dateRange ? 1 : 0}
            >
              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label>选择日期范围</Label>
                  <div className="flex items-center space-x-2">
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            "justify-start text-left font-normal flex-1",
                            !tempDateRange.start && "text-muted-foreground"
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {tempDateRange.start ? (
                            format(tempDateRange.start, "yyyy-MM-dd", { locale: zhCN })
                          ) : (
                            "开始日期"
                          )}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0">
                        <Calendar
                          mode="single"
                          selected={tempDateRange.start}
                          onSelect={(date) => setTempDateRange(prev => ({ ...prev, start: date }))}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                    
                    <span className="text-muted-foreground">至</span>
                    
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            "justify-start text-left font-normal flex-1",
                            !tempDateRange.end && "text-muted-foreground"
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {tempDateRange.end ? (
                            format(tempDateRange.end, "yyyy-MM-dd", { locale: zhCN })
                          ) : (
                            "结束日期"
                          )}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0">
                        <Calendar
                          mode="single"
                          selected={tempDateRange.end}
                          onSelect={(date) => setTempDateRange(prev => ({ ...prev, end: date }))}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                  
                  <div className="flex justify-between">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setTempDateRange({})}
                    >
                      清除
                    </Button>
                    <Button
                      size="sm"
                      onClick={applyDateRange}
                      disabled={!tempDateRange.start || !tempDateRange.end}
                    >
                      应用
                    </Button>
                  </div>
                </div>

                {/* 当前活跃的日期过滤器 */}
                {filters.dateRange && (
                  <div className="flex items-center justify-between p-2 bg-primary/10 rounded">
                    <span className="text-sm">
                      {format(filters.dateRange.start, "yyyy-MM-dd", { locale: zhCN })} 至{' '}
                      {format(filters.dateRange.end, "yyyy-MM-dd", { locale: zhCN })}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => clearFilter('dateRange')}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                )}
              </div>
            </FilterSection>

            {/* 状态过滤 */}
            <FilterSection
              title="状态"
              icon={Tags}
              sectionKey="status"
              activeCount={filters.status?.length || 0}
            >
              <div className="space-y-3">
                {defaultAvailableData.statuses.map((status) => (
                  <div key={status} className="flex items-center space-x-2">
                    <Checkbox
                      id={`status-${status}`}
                      checked={filters.status?.includes(status) || false}
                      onCheckedChange={(checked) => {
                        const currentStatus = filters.status || [];
                        if (checked) {
                          updateFilters('status', [...currentStatus, status]);
                        } else {
                          updateFilters('status', currentStatus.filter(s => s !== status));
                        }
                      }}
                    />
                    <Label htmlFor={`status-${status}`} className="text-sm">
                      {statusLabels[status] || status}
                    </Label>
                  </div>
                ))}
              </div>
            </FilterSection>

            {/* 参与者过滤 */}
            <FilterSection
              title="参与者"
              icon={Users}
              sectionKey="participants"
              activeCount={filters.participants?.length || 0}
            >
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label>搜索参与者</Label>
                  <Input placeholder="输入参与者姓名..." />
                </div>
                <ScrollArea className="max-h-40">
                  <div className="space-y-2">
                    {defaultAvailableData.participants.map((participant) => (
                      <div key={participant} className="flex items-center space-x-2">
                        <Checkbox
                          id={`participant-${participant}`}
                          checked={filters.participants?.includes(participant) || false}
                          onCheckedChange={(checked) => {
                            const currentParticipants = filters.participants || [];
                            if (checked) {
                              updateFilters('participants', [...currentParticipants, participant]);
                            } else {
                              updateFilters('participants', currentParticipants.filter(p => p !== participant));
                            }
                          }}
                        />
                        <Label htmlFor={`participant-${participant}`} className="text-sm">
                          {participant}
                        </Label>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </FilterSection>

            {/* 分类过滤 */}
            <FilterSection
              title="分类"
              icon={Tags}
              sectionKey="categories"
              activeCount={filters.categories?.length || 0}
            >
              <div className="space-y-2">
                {defaultAvailableData.categories.map((category) => (
                  <div key={category} className="flex items-center space-x-2">
                    <Checkbox
                      id={`category-${category}`}
                      checked={filters.categories?.includes(category) || false}
                      onCheckedChange={(checked) => {
                        const currentCategories = filters.categories || [];
                        if (checked) {
                          updateFilters('categories', [...currentCategories, category]);
                        } else {
                          updateFilters('categories', currentCategories.filter(c => c !== category));
                        }
                      }}
                    />
                    <Label htmlFor={`category-${category}`} className="text-sm">
                      {category}
                    </Label>
                  </div>
                ))}
              </div>
            </FilterSection>

            {/* 类型过滤 */}
            <FilterSection
              title="类型"
              icon={FileType}
              sectionKey="types"
              activeCount={filters.types?.length || 0}
            >
              <div className="space-y-2">
                {defaultAvailableData.types.map((type) => (
                  <div key={type} className="flex items-center space-x-2">
                    <Checkbox
                      id={`type-${type}`}
                      checked={filters.types?.includes(type) || false}
                      onCheckedChange={(checked) => {
                        const currentTypes = filters.types || [];
                        if (checked) {
                          updateFilters('types', [...currentTypes, type]);
                        } else {
                          updateFilters('types', currentTypes.filter(t => t !== type));
                        }
                      }}
                    />
                    <Label htmlFor={`type-${type}`} className="text-sm">
                      {type}
                    </Label>
                  </div>
                ))}
              </div>
            </FilterSection>

            {/* 内容特性过滤 */}
            <FilterSection
              title="内容特性"
              icon={FileType}
              sectionKey="content"
              activeCount={
                (filters.hasTranscription ? 1 : 0) +
                (filters.hasNotes ? 1 : 0) +
                (filters.hasAIEnhancement ? 1 : 0)
              }
            >
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="has-transcription"
                    checked={filters.hasTranscription || false}
                    onCheckedChange={(checked) => updateFilters('hasTranscription', checked)}
                  />
                  <Label htmlFor="has-transcription" className="text-sm">
                    包含转录内容
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="has-notes"
                    checked={filters.hasNotes || false}
                    onCheckedChange={(checked) => updateFilters('hasNotes', checked)}
                  />
                  <Label htmlFor="has-notes" className="text-sm">
                    包含笔记
                  </Label>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="has-ai-enhancement"
                    checked={filters.hasAIEnhancement || false}
                    onCheckedChange={(checked) => updateFilters('hasAIEnhancement', checked)}
                  />
                  <Label htmlFor="has-ai-enhancement" className="text-sm">
                    包含AI增强内容
                  </Label>
                </div>
              </div>
            </FilterSection>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}