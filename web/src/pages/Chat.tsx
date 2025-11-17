import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { MessageList } from '@/components/MessageList';
import { ChatInput } from '@/components/ChatInput';
import { SearchDialog } from '@/components/SearchDialog';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';
import { useChat } from '@/hooks/useChat';
import { useConversations } from '@/hooks/useConversations';
import { LogOutIcon, SettingsIcon, SearchIcon, MoonIcon, SunIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';

export const Chat = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const { messages, isSending, sendMessageStream, stopStreaming } = useChat();
  const { conversations, selectConversation, currentConversation, resetConversation } = useConversations();
  const { toast } = useToast();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  const handleLogout = () => {
    logout();
  };

  const handleSelectConversation = async (threadId: string) => {
    const conversation = conversations.find((c) => c.thread_id === threadId);
    if (conversation) {
      await selectConversation(conversation);
    }
  };

  const handleResetCurrentConversation = async () => {
    if (!currentConversation) return;
    setIsResetDialogOpen(true);
  };

  const confirmReset = async () => {
    if (!currentConversation) return;
    try {
      await resetConversation(currentConversation.thread_id);
      toast({
        title: '重置成功',
        description: '对话已重置，所有消息已清空',
      });
      setIsResetDialogOpen(false);
    } catch (error) {
      console.error('Failed to reset conversation:', error);
      toast({
        title: '重置失败',
        description: '重置对话时发生错误',
        variant: 'destructive',
      });
    }
  };

  // 快捷键支持
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-16 border-b flex items-center justify-between px-6 bg-card">
          <h1 className="text-xl font-semibold">AI Agent</h1>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              欢迎，{user?.nickname || user?.username}
            </span>
            <Separator orientation="vertical" className="h-6" />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsSearchOpen(true)}
              title="搜索 (Ctrl+K)"
            >
              <SearchIcon size={16} className="mr-2" />
              搜索
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              title={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
            >
              {theme === 'light' ? <MoonIcon size={16} /> : <SunIcon size={16} />}
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/settings">
                <SettingsIcon size={16} className="mr-2" />
                设置
              </Link>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
            >
              <LogOutIcon size={16} className="mr-2" />
              退出
            </Button>
          </div>
        </div>

        {/* Messages */}
        <MessageList messages={messages} />

        {/* Input */}
        <ChatInput
          onSend={sendMessageStream}
          onStop={stopStreaming}
          onReset={handleResetCurrentConversation}
          disabled={isSending}
          isSending={isSending}
          showReset={!!currentConversation}
        />
      </div>

      {/* Search Dialog */}
      <SearchDialog
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onSelectConversation={handleSelectConversation}
      />

      {/* Reset Confirmation Dialog */}
      <Dialog open={isResetDialogOpen} onOpenChange={setIsResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重置对话</DialogTitle>
            <DialogDescription>
              确定要重置当前对话吗？所有消息将被清空，此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsResetDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmReset}>
              确定重置
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
