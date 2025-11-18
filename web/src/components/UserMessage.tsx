import { CheckIcon, CopyIcon, UserIcon } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import type { Message } from '@/stores/chatStore';
import { formatTime } from '@/utils/date';

interface UserMessageProps {
  message: Message;
  onCopy: (content: string, id: number) => void;
  copiedId: number | null;
}

export const UserMessage = ({ message, onCopy, copiedId }: UserMessageProps) => {
  return (
    <div className="flex gap-4 items-start animate-slide-up">
      <div className="flex-shrink-0 w-10 h-10" />

      <div className="flex-1 flex justify-end">
        <div className="max-w-[85%] sm:max-w-[80%] md:max-w-[75%]">
          <div className="relative rounded-2xl px-4 py-3 shadow-md transition-all duration-200 hover:shadow-lg bg-gradient-to-br from-emerald-400 to-slate-500 text-white">
            <div className="whitespace-pre-wrap">{message.content}</div>
          </div>

          {!message.isStreaming && (
            <div className="flex items-center justify-between gap-2 mt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onCopy(message.content, message.id)}
                className="h-6 text-xs text-muted-foreground"
                title="复制"
              >
                {copiedId === message.id ? (
                  <>
                    <CheckIcon size={12} className="mr-1" />
                    已复制
                  </>
                ) : (
                  <>
                    <CopyIcon size={12} className="mr-1" />
                    复制
                  </>
                )}
              </Button>
              {message.created_at && (
                <span className="text-xs text-muted-foreground" title={message.created_at}>
                  {formatTime(message.created_at)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <Avatar className="flex-shrink-0 w-10 h-10 ring-2 ring-primary/20 shadow-md">
        <AvatarFallback className="bg-gradient-to-br from-emerald-400 to-slate-500">
          <UserIcon size={20} className="text-white" />
        </AvatarFallback>
      </Avatar>
    </div>
  );
};
