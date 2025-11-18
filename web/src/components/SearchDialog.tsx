import { SearchIcon } from 'lucide-react';
import { useState } from 'react';
import type { SearchRequest } from '@/api/aPIDoc';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import request from '@/utils/request';

interface SearchDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (threadId: string) => void;
}

export const SearchDialog = ({ isOpen, onClose, onSelectConversation }: SearchDialogProps) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const { toast } = useToast();

  const handleSearch = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setSearched(true);
      const data: SearchRequest = {
        query: query.trim(),
        skip: 0,
        limit: 20,
      };
      const response = await request.post('/conversations/search', data);
      // 解析 BaseResponse 包装的数据
      if (response.data.success && response.data.data) {
        setResults(response.data.data.results || []);
        if (response.data.data.results?.length === 0) {
          toast({
            title: '未找到结果',
            description: '没有找到匹配的会话或消息',
          });
        }
      } else {
        setResults([]);
      }
    } catch (error) {
      console.error('Search failed:', error);
      setResults([]);
      toast({
        title: '搜索失败',
        description: '搜索时发生错误，请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleSelectResult = (threadId: string) => {
    onSelectConversation(threadId);
    onClose();
    setQuery('');
    setResults([]);
    setSearched(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>搜索会话和消息</DialogTitle>
          <DialogDescription>输入关键词搜索会话标题和消息内容</DialogDescription>
        </DialogHeader>

        {/* Search Input */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <SearchIcon
              size={20}
              className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground"
            />
            <Input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="搜索会话和消息..."
              className="pl-10"
              autoFocus
            />
          </div>
          <Button onClick={handleSearch} disabled={loading || !query.trim()}>
            搜索
          </Button>
        </div>

        <Separator />

        {/* Results */}
        <ScrollArea className="max-h-96">
          {loading && <div className="text-center text-muted-foreground py-8">搜索中...</div>}

          {!loading && searched && results.length === 0 && (
            <div className="text-center text-muted-foreground py-8">没有找到匹配的结果</div>
          )}

          {!loading && !searched && (
            <div className="text-center text-muted-foreground py-8">输入关键词并按 Enter 搜索</div>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-3">
              {results.map((result, index) => (
                <div
                  key={index}
                  onClick={() => handleSelectResult(result.thread_id)}
                  className="p-4 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                >
                  <div className="font-medium mb-1">{result.title || '未命名会话'}</div>
                  {result.content && <div className="text-sm text-muted-foreground line-clamp-2">{result.content}</div>}
                  <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                    {result.role && (
                      <span className="px-2 py-1 bg-muted rounded">{result.role === 'user' ? '用户' : '助手'}</span>
                    )}
                    {result.created_at && <span>{new Date(result.created_at).toLocaleString()}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Footer */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
          <div className="flex items-center gap-2">
            <kbd className="px-2 py-1 bg-muted border rounded">Enter</kbd>
            <span>搜索</span>
            <Separator orientation="vertical" className="h-4 mx-2" />
            <kbd className="px-2 py-1 bg-muted border rounded">Esc</kbd>
            <span>关闭</span>
          </div>
          {results.length > 0 && <div>找到 {results.length} 个结果</div>}
        </div>
      </DialogContent>
    </Dialog>
  );
};
