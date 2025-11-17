import { useState } from 'react';
import { PlusIcon, MessageSquareIcon, TrashIcon, EditIcon, CheckIcon, XIcon } from 'lucide-react';
import { useConversations } from '@/hooks/useConversations';
import { useChatStore } from '@/stores/chatStore';
import { ConversationResponse } from '@/api/aPIDoc';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { ScrollArea } from '@/components/ui/scroll-area';

export const Sidebar = () => {
  const {
    conversations,
    currentConversation,
    selectConversation,
    updateConversationTitle,
    removeConversation,
  } = useConversations();
  const { setCurrentConversation, setMessages } = useChatStore();
  const { toast } = useToast();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [targetConversationId, setTargetConversationId] = useState<string | null>(null);

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
    <div className="w-64 border-r bg-card flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b">
        <Button
          onClick={handleCreateConversation}
          className="w-full"
          size="sm"
        >
          <PlusIcon size={16} className="mr-2" />
          新建对话
        </Button>
      </div>

      {/* Conversation List */}
      <ScrollArea className="flex-1">
        {conversations.map((conversation) => (
          <div
            key={conversation.thread_id}
            className={`group relative px-3 py-3 cursor-pointer hover:bg-accent transition-colors ${
              currentConversation?.thread_id === conversation.thread_id
                ? 'bg-accent'
                : ''
            }`}
            onClick={() => selectConversation(conversation)}
          >
            {editingId === conversation.thread_id ? (
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
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleCancelEdit}
                  className="h-8 w-8"
                >
                  <XIcon size={14} />
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <MessageSquareIcon size={16} className="flex-shrink-0 text-muted-foreground" />
                <span className="flex-1 text-sm truncate">{conversation.title}</span>
                <div className="hidden group-hover:flex items-center gap-1">
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
              </div>
            )}
          </div>
        ))}
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t">
        <div className="text-xs text-muted-foreground">
          共 {conversations.length} 个对话
        </div>
      </div>

      {/* Delete Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除对话</DialogTitle>
            <DialogDescription>
              确定要删除这个对话吗？此操作不可恢复。
            </DialogDescription>
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
  );
};
