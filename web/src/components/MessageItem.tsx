import { BotIcon } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Message } from '@/stores/chatStore';
import { UserMessage } from './UserMessage';
import { AIMessage } from './AIMessage';
import { ToolCallMessage } from './ToolCallMessage';

interface MessageItemProps {
  message: Message & {
    isToolCall?: boolean;
    toolCall?: {
      name: string;
      arguments?: any;
      input?: any;
      output?: any;
    };
  };
  onCopy: (content: string, id: number) => void;
  copiedId: number | null;
}

export const MessageItem = ({ message, onCopy, copiedId }: MessageItemProps) => {
  // 用户消息
  if (message.role === 'user') {
    return <UserMessage message={message} onCopy={onCopy} copiedId={copiedId} />;
  }

  // 工具调用消息
  if (message.isToolCall && message.toolCall) {
    return (
      <div className="flex gap-4 items-start animate-slide-up">
        <Avatar className="flex-shrink-0 w-10 h-10 ring-2 ring-primary/20 shadow-md">
          <AvatarFallback className="bg-gradient-to-br from-orange-500 to-red-600">
            🔧
          </AvatarFallback>
        </Avatar>

        <div className="flex-1 max-w-[90%]">
          <div className="relative rounded-2xl px-4 py-3 shadow-md transition-all duration-200 hover:shadow-lg bg-orange-50 dark:bg-orange-950/30 text-foreground border-2 border-orange-300 dark:border-orange-700">
            <ToolCallMessage toolCall={message.toolCall} messageId={message.id} />
          </div>
        </div>

        <div className="flex-shrink-0 w-10 h-10" />
      </div>
    );
  }

  // AI 消息
  return <AIMessage message={message} onCopy={onCopy} copiedId={copiedId} />;
};
