import {
  CheckIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EditIcon,
  MenuIcon,
  MessageSquareIcon,
  PlusIcon,
  TrashIcon,
  XIcon,
} from 'lucide-react';
import { useState } from 'react';
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

export const Sidebar = () => {
  const { conversations, currentConversation, selectConversation, updateConversationTitle, removeConversation } =
    useConversations();
  const { setCurrentConversation, setMessages } = useChatStore();
  const { toast } = useToast();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [targetConversationId, setTargetConversationId] = useState<string | null>(null);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const handleCreateConversation = () => {
    // 不再直接创建空会话，而是清空当前选择，让用户开始新对话
    // 当用户发送第一条消息时，系统会自动创建会话
    setCurrentConversation(null);
    setMessages([]);
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

      {/* Sidebar */}
      <div
        className={`
        fixed md:relative
        border-r bg-card flex flex-col h-screen
        z-40
        transition-all duration-300 ease-in-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        ${isCollapsed ? 'md:w-16' : 'w-72 sm:w-80 md:w-64 lg:w-72 xl:w-80'}
      `}
      >
        {/* Desktop Collapse Toggle Button */}
        <Button
          variant="ghost"
          size="icon"
          className="hidden md:flex absolute -right-3 top-6 z-50 h-6 w-6 rounded-full border bg-background shadow-md hover:bg-accent"
          onClick={() => setIsCollapsed(!isCollapsed)}
          title={isCollapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          {isCollapsed ? <ChevronRightIcon size={14} /> : <ChevronLeftIcon size={14} />}
        </Button>

        {/* Header */}
        <div className="p-4 border-b">
          <Button
            onClick={() => {
              handleCreateConversation();
              setIsMobileOpen(false);
            }}
            className={`w-full ${isCollapsed ? 'px-0' : ''}`}
            size={isCollapsed ? 'icon' : 'sm'}
            title={isCollapsed ? '新建对话' : ''}
          >
            <PlusIcon size={16} className={isCollapsed ? '' : 'mr-2'} />
            {!isCollapsed && '新建对话'}
          </Button>
        </div>

        {/* Conversation List */}
        <ScrollArea className="flex-1">
          {conversations.map((conversation) => (
            <div
              key={conversation.thread_id}
              className={`group relative px-3 py-3 cursor-pointer hover:bg-accent transition-all duration-200 border-l-4 ${
                currentConversation?.thread_id === conversation.thread_id
                  ? 'bg-accent border-l-emerald-500'
                  : 'border-l-transparent'
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
                <div className={`flex items-center gap-2 ${isCollapsed ? 'justify-center' : ''}`}>
                  <MessageSquareIcon
                    size={16}
                    className={`flex-shrink-0 text-muted-foreground ${isCollapsed ? 'mx-auto' : ''}`}
                  />
                  {!isCollapsed && (
                    <>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{conversation.title}</div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className="truncate">
                            {conversation.message_count ? `${conversation.message_count} 条消息` : '暂无消息'}
                          </span>
                          <span>·</span>
                          <span className="flex-shrink-0">{formatDate(conversation.updated_at)}</span>
                        </div>
                      </div>
                      <div className="hidden group-hover:flex items-center gap-1 flex-shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(conversation);
                          }}
                          className="h-6 w-6"
                          title="重命名"
                        >
                          <EditIcon size={12} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => handleDelete(conversation.thread_id, e)}
                          className="h-6 w-6 text-destructive hover:text-destructive"
                          title="删除"
                        >
                          <TrashIcon size={12} />
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </ScrollArea>

        {/* Footer */}
        {!isCollapsed && (
          <div className="p-4 border-t">
            <div className="text-xs text-muted-foreground">共 {conversations.length} 个对话</div>
          </div>
        )}

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
