import { LogOutIcon, MoonIcon, SearchIcon, SettingsIcon, SunIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChatInput } from '@/components/ChatInput';
import { MessageList } from '@/components/MessageList';
import { SearchDialog } from '@/components/SearchDialog';
import { Sidebar } from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { useChat } from '@/hooks/useChat';
import { useConversations } from '@/hooks/useConversations';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';
import { useUserSettingsStore } from '@/stores/userSettingsStore';

export const Chat = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const { settings, loadSettings } = useUserSettingsStore();
  const { messages, isSending, sendMessageStream, stopStreaming } = useChat();
  const { conversations, selectConversation, currentConversation, resetConversation, loadConversations } =
    useConversations();
  const { toast } = useToast();
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);

  // 处理新会话创建
  const handleNewConversation = async (threadId: string) => {
    // 重新加载会话列表以获取新创建的会话
    await loadConversations();
    // 选择新创建的会话
    const conversation = conversations.find((c) => c.thread_id === threadId);
    if (conversation) {
      await selectConversation(conversation);
    }
  };

  // 包装 sendMessageStream 以处理新会话
  const handleSendMessage = async (content: string) => {
    await sendMessageStream(content, handleNewConversation);
  };

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    } else {
      // 加载用户设置
      loadSettings();
    }
  }, [isAuthenticated, navigate, loadSettings]);

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
        <div className="h-16 border-b flex items-center justify-between px-4 sm:px-6 lg:px-8 bg-card">
          <div className="flex items-center gap-2 ml-12 md:ml-0">
            <h1 className="text-lg sm:text-xl font-semibold">AI Agent</h1>
            <span className="text-xs text-muted-foreground hidden sm:inline">
              {settings.llm_model || 'Qwen/Qwen3-8B'}
            </span>
          </div>
          <div className="flex items-center gap-0.5 sm:gap-1 md:gap-2">
            <span className="hidden lg:inline text-sm text-muted-foreground mr-2">
              欢迎，{user?.nickname || user?.username}
            </span>
            <Separator orientation="vertical" className="h-6 hidden lg:block mr-2" />
            <Button variant="ghost" size="icon" onClick={() => setIsSearchOpen(true)} title="搜索 (Ctrl+K)">
              <SearchIcon size={16} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              title={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
            >
              {theme === 'light' ? <MoonIcon size={16} /> : <SunIcon size={16} />}
            </Button>
            <Button variant="ghost" size="icon" asChild>
              <Link to="/settings">
                <SettingsIcon size={16} />
              </Link>
            </Button>
            <Button variant="ghost" size="icon" onClick={handleLogout} title="退出登录">
              <LogOutIcon size={16} />
            </Button>
          </div>
        </div>

        {/* Messages */}
        <MessageList messages={messages} />

        {/* Input */}
        <ChatInput
          onSend={handleSendMessage}
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
            <DialogDescription>确定要重置当前对话吗？所有消息将被清空，此操作不可恢复。</DialogDescription>
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
