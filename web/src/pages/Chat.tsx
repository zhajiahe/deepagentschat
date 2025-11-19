import { FolderOpen, LogOutIcon, MoonIcon, SettingsIcon, SunIcon } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChatInput } from '@/components/ChatInput';
import { EmptyState } from '@/components/EmptyState';
import { FileBrowser } from '@/components/FileBrowser';
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
import { useChatStore } from '@/stores/chatStore';
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
  const [isFileBrowserOpen, setIsFileBrowserOpen] = useState(false);

  // 处理新会话创建
  const handleNewConversation = async (threadId: string) => {
    // 重新加载会话列表以获取新创建的会话
    await loadConversations();
    // 只更新当前会话，不重新加载消息（消息已经在本地了）
    // 从 store 中获取最新的会话列表
    const latestConversations = useChatStore.getState().conversations;
    const conversation = latestConversations.find((c) => c.thread_id === threadId);
    if (conversation) {
      // 使用 useChatStore 直接设置当前会话，不触发消息加载
      useChatStore.getState().setCurrentConversation(conversation);
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
    <div className="flex h-screen bg-background dark:bg-grokbg text-foreground dark:text-groktext overflow-hidden">
      {/* Sidebar - Grok 左侧侧边栏，宽度 260px */}
      <Sidebar onSearchOpen={() => setIsSearchOpen(true)} />

      {/* Main Chat Area - Grok 右侧聊天区 */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${isFileBrowserOpen ? 'mr-80' : ''}`}>
        {/* Header - 简化的顶部栏 */}
        <div className="h-14 flex items-center justify-between px-4 sm:px-6 bg-card dark:bg-grokbg">
          <div className="flex items-center gap-2 ml-12 md:ml-0">
            <h1 className="text-base sm:text-lg font-semibold text-foreground dark:text-groktext">AI Agent</h1>
            <span className="text-xs text-muted-foreground dark:text-groksub hidden sm:inline">
              {settings.llm_model || 'Qwen/Qwen3-8B'}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsFileBrowserOpen(!isFileBrowserOpen)}
              title="文件浏览器"
              className="text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext"
            >
              <FolderOpen size={18} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              title={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
              className="text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext"
            >
              {theme === 'light' ? <MoonIcon size={18} /> : <SunIcon size={18} />}
            </Button>
            <Button
              variant="ghost"
              size="icon"
              asChild
              className="text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext"
            >
              <Link to="/settings">
                <SettingsIcon size={18} />
              </Link>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="退出登录"
              className="text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext"
            >
              <LogOutIcon size={18} />
            </Button>
          </div>
        </div>

        {/* Messages or Empty State */}
        {messages.length === 0 ? (
          <EmptyState onNewChat={() => {/* 可选：点击建议卡片时的处理 */}} />
        ) : (
          <MessageList messages={messages} />
        )}

        {/* Input - Grok 固定底部输入框 */}
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

      {/* File Browser */}
      <FileBrowser isOpen={isFileBrowserOpen} onClose={() => setIsFileBrowserOpen(false)} />
    </div>
  );
};
