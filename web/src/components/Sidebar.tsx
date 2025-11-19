import {
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EditIcon,
  HistoryIcon,
  LogOutIcon,
  MenuIcon,
  MessageSquareIcon,
  PlusIcon,
  SearchIcon,
  SettingsIcon,
  TrashIcon,
  XIcon,
} from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { ConversationResponse } from '@/api/aPIDoc';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { useConversations } from '@/hooks/useConversations';
import { useChatStore } from '@/stores/chatStore';
import { formatDate } from '@/utils/date';

interface SidebarProps {
  onSearchOpen?: () => void;
}

export const Sidebar = ({ onSearchOpen }: SidebarProps) => {
  const { conversations, currentConversation, selectConversation, updateConversationTitle, removeConversation } =
    useConversations();
  const { setCurrentConversation, setMessages } = useChatStore();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [targetConversationId, setTargetConversationId] = useState<string | null>(null);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showHistoryPopover, setShowHistoryPopover] = useState(false);

  const handleCreateConversation = () => {
    // 不再直接创建空会话，而是清空当前选择，让用户开始新对话
    // 当用户发送第一条消息时，系统会自动创建会话
    setMessages([]);
    setCurrentConversation(null);
  };

  const handleStartEdit = (conversation: ConversationResponse) => {
    setEditingId(conversation.thread_id);
    setEditTitle(conversation.title);
  };

  const handleSaveEdit = async (threadId: string) => {
    if (editTitle.trim()) {
      try {
        await updateConversationTitle(threadId, editTitle.trim());
        setEditingId(null);
      } catch (error) {
        console.error('Failed to update title:', error);
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  const handleDelete = async (threadId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setTargetConversationId(threadId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!targetConversationId) return;
    try {
      await removeConversation(targetConversationId);
      toast({
        title: '删除成功',
        description: '对话已删除',
      });
      setDeleteDialogOpen(false);
      setTargetConversationId(null);
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      toast({
        title: '删除失败',
        description: '删除对话时发生错误',
        variant: 'destructive',
      });
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    navigate('/login');
  };

  return (
    <>
      {/* Mobile Toggle Button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 md:hidden"
        onClick={() => setIsMobileOpen(!isMobileOpen)}
      >
        <MenuIcon size={20} />
      </Button>

      {/* Overlay for mobile */}
      {isMobileOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setIsMobileOpen(false)} />
      )}

      {/* Sidebar - Grok Style */}
      <div
        className={`
        fixed md:relative
        bg-card dark:bg-grokbg border-r border-border dark:border-grokborder flex flex-col h-screen
        z-40
        transition-all duration-300 ease-in-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${isCollapsed ? 'md:w-16' : 'w-64'}
      `}
      >
        {/* Logo */}
        <div className={`p-4 border-b border-border dark:border-grokborder ${isCollapsed ? 'flex justify-center' : ''}`}>
          {isCollapsed ? (
            <img src="/logo.svg" alt="DeepAgents" className="h-8 w-8" />
          ) : (
            <div className="flex items-center gap-3">
              <img src="/logo.svg" alt="DeepAgents" className="h-8 w-8" />
              <div>
                <h1 className="text-lg font-bold text-foreground dark:text-groktext">DeepAgents</h1>
                <p className="text-xs text-muted-foreground dark:text-groksub">AI Chat Assistant</p>
              </div>
            </div>
          )}
        </div>

        {/* Header - Grok 新对话按钮和搜索 */}
        <div className="p-3 space-y-2">
          <Button
            onClick={() => {
              handleCreateConversation();
              setIsMobileOpen(false);
            }}
            variant="outline"
            className={`w-full border-border dark:border-grokborder hover:bg-accent dark:hover:bg-grokgray/50 text-foreground dark:text-groktext rounded-grok transition-colors ${isCollapsed ? 'px-0' : ''}`}
            size={isCollapsed ? 'icon' : 'default'}
            title={isCollapsed ? '新建对话' : ''}
          >
            <PlusIcon size={20} className={isCollapsed ? '' : 'mr-3'} />
            {!isCollapsed && <span className="text-sm font-medium">New chat</span>}
          </Button>

          {/* 搜索按钮 */}
          <Button
            variant="ghost"
            onClick={onSearchOpen}
            className={`w-full dark:hover:bg-grokgray/50 transition-colors ${isCollapsed ? 'px-0' : 'justify-start'}`}
            size={isCollapsed ? 'icon' : 'default'}
            title={isCollapsed ? '搜索对话 (⌘K)' : ''}
          >
            <SearchIcon size={18} className={isCollapsed ? '' : 'mr-3'} />
            {!isCollapsed && <span className="text-sm">搜索对话</span>}
            {!isCollapsed && (
              <kbd className="ml-auto pointer-events-none inline-flex h-5 select-none items-center gap-1 rounded border border-border dark:border-grokborder bg-muted dark:bg-grokgray px-1.5 font-mono text-[10px] font-medium text-muted-foreground dark:text-groksub opacity-100">
                <span className="text-xs">⌘</span>K
              </kbd>
            )}
          </Button>

          {/* 折叠时显示历史对话图标和搜索图标 */}
          {isCollapsed && (
            <div
              className="relative"
              onMouseEnter={() => setShowHistoryPopover(true)}
              onMouseLeave={() => setShowHistoryPopover(false)}
            >
              <Button
                variant="ghost"
                size="icon"
                className="w-full dark:hover:bg-grokgray/50"
                title="历史对话"
              >
                <HistoryIcon size={20} />
              </Button>

              {/* 悬浮的对话列表 */}
              {showHistoryPopover && conversations.length > 0 && (
                <div
                  className="absolute left-full ml-1 top-0 w-64 max-h-96 bg-card dark:bg-grokgray border border-border dark:border-grokborder rounded-lg shadow-xl overflow-hidden z-50"
                >
                  <div className="p-2 border-b border-border dark:border-grokborder">
                    <div className="text-sm font-medium text-foreground dark:text-groktext">历史对话</div>
                  </div>
                  <ScrollArea className="max-h-80">
                    {conversations.map((conversation) => (
                      <button
                        key={conversation.thread_id}
                        onClick={() => {
                          selectConversation(conversation);
                          setShowHistoryPopover(false);
                          setIsMobileOpen(false);
                        }}
                        className={`w-full text-left px-3 py-2 hover:bg-accent dark:hover:bg-grokgray/50 transition-colors ${
                          currentConversation?.thread_id === conversation.thread_id
                            ? 'bg-accent dark:bg-grokgray/80'
                            : ''
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <MessageSquareIcon size={14} className="flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm truncate">{conversation.title || 'New conversation'}</div>
                            <div className="text-xs text-muted-foreground dark:text-groksub">
                              {conversation.message_count || 0} 条消息
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Conversation List - Grok Style - 折叠时隐藏 */}
        {!isCollapsed && (
          <ScrollArea className="flex-1 px-3">
            {conversations.map((conversation) => (
            <div
              key={conversation.thread_id}
              className={`group relative mb-1 cursor-pointer transition-colors rounded-lg ${
                currentConversation?.thread_id === conversation.thread_id
                  ? 'bg-accent dark:bg-grokgray/80 text-foreground dark:text-white'
                  : 'text-muted-foreground dark:text-groksub hover:bg-accent/50 dark:hover:bg-grokgray/50'
              }`}
              onClick={() => {
                selectConversation(conversation);
                setIsMobileOpen(false);
              }}
            >
              {editingId === conversation.thread_id && !isCollapsed ? (
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <Input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="flex-1 h-8 text-sm"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        handleSaveEdit(conversation.thread_id);
                      } else if (e.key === 'Escape') {
                        handleCancelEdit();
                      }
                    }}
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleSaveEdit(conversation.thread_id)}
                    className="h-8 w-8"
                  >
                    <CheckIcon size={14} />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={handleCancelEdit} className="h-8 w-8">
                    <XIcon size={14} />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <MessageSquareIcon size={16} className="flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm truncate">{conversation.title || 'New conversation'}</div>
                  </div>
                  <div className="hidden group-hover:flex items-center gap-1 flex-shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartEdit(conversation);
                      }}
                      className="h-6 w-6 hover:bg-accent dark:hover:bg-grokgray"
                      title="重命名"
                    >
                      <EditIcon size={12} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => handleDelete(conversation.thread_id, e)}
                      className="h-6 w-6 text-destructive hover:text-destructive hover:bg-accent dark:hover:bg-grokgray"
                      title="删除"
                    >
                      <TrashIcon size={12} />
                    </Button>
                  </div>
                </div>
              )}
            </div>
            ))}
          </ScrollArea>
        )}

        {/* Footer - Grok Style */}
        <div className="p-3 space-y-2 border-t border-border dark:border-grokborder">
          {/* 设置和登出按钮 */}
          {!isCollapsed ? (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="default"
                asChild
                className="flex-1 justify-start text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext hover:bg-accent dark:hover:bg-grokgray/50"
              >
                <Link to="/settings">
                  <SettingsIcon size={18} className="mr-3" />
                  <span className="text-sm">设置</span>
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="default"
                onClick={handleLogout}
                className="flex-1 justify-start text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext hover:bg-accent dark:hover:bg-grokgray/50"
              >
                <LogOutIcon size={18} className="mr-3" />
                <span className="text-sm">退出</span>
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Button
                variant="ghost"
                size="icon"
                asChild
                className="w-full text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext hover:bg-accent dark:hover:bg-grokgray/50"
                title="设置"
              >
                <Link to="/settings">
                  <SettingsIcon size={18} />
                </Link>
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                className="w-full text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext hover:bg-accent dark:hover:bg-grokgray/50"
                title="退出登录"
              >
                <LogOutIcon size={18} />
              </Button>
            </div>
          )}

          {/* Desktop Collapse Toggle Button - 底部 */}
          <div className={`hidden md:flex ${isCollapsed ? 'justify-center' : 'justify-end'}`}>
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 rounded-full border border-border dark:border-grokborder bg-background dark:bg-grokbg shadow-sm hover:bg-accent dark:hover:bg-grokgray"
              onClick={() => setIsCollapsed(!isCollapsed)}
              title={isCollapsed ? '展开侧边栏' : '收起侧边栏'}
            >
              {isCollapsed ? <ChevronRightIcon size={14} /> : <ChevronLeftIcon size={14} />}
            </Button>
          </div>
        </div>

        {/* Delete Dialog */}
        <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>删除对话</DialogTitle>
              <DialogDescription>确定要删除这个对话吗？此操作不可恢复。</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                取消
              </Button>
              <Button variant="destructive" onClick={confirmDelete}>
                确定删除
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  );
};
