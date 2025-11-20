import { CheckIcon, CopyIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { UserMessage as UserMessageType } from '@/stores/chatStore';
import { formatTime } from '@/utils/date';

interface UserMessageProps {
  message: UserMessageType & { role: 'user' };
  onCopy: (content: string, id: number) => void;
  copiedId: number | null;
}

export const UserMessage = ({ message, onCopy, copiedId }: UserMessageProps) => {
  return (
    <div className="max-w-3xl w-full mx-auto px-4 animate-slide-up">
      <div className="bg-primary dark:bg-grokblue ml-auto rounded-grok px-5 py-4 text-white max-w-fit">
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>

      {!message.isStreaming && (
        <div className="flex items-center justify-end gap-2 mt-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onCopy(message.content, message.id)}
            className="h-6 text-xs text-muted-foreground dark:text-groksub hover:text-foreground dark:hover:text-groktext"
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
            <span className="text-xs text-muted-foreground dark:text-groksub" title={message.created_at}>
              {formatTime(message.created_at)}
            </span>
          )}
        </div>
      )}
    </div>
  );
};
