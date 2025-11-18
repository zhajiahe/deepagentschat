import { BotIcon, CheckIcon, CopyIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import type { Message } from '@/stores/chatStore';
import { formatTime } from '@/utils/date';

interface AIMessageProps {
  message: Message;
  onCopy: (content: string, id: number) => void;
  copiedId: number | null;
}

export const AIMessage = ({ message, onCopy, copiedId }: AIMessageProps) => {
  return (
    <div className="flex gap-4 items-start animate-slide-up">
      <Avatar className="flex-shrink-0 w-10 h-10 ring-2 ring-primary/20 shadow-md">
        <AvatarFallback className="bg-gradient-to-br from-emerald-400 to-slate-500">
          <BotIcon size={20} className="text-white" />
        </AvatarFallback>
      </Avatar>

      <div className="flex-1 max-w-[90%]">
        <div className="relative rounded-2xl px-4 py-3 shadow-md transition-all duration-200 hover:shadow-lg bg-muted/50 dark:bg-muted text-foreground border border-border">
          <div className="prose prose-base max-w-none dark:prose-invert prose-pre:bg-gray-900 prose-pre:text-gray-100 w-full">
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
            {message.isStreaming && (
              <span className="inline-flex gap-1 ml-2 items-center">
                <span
                  className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <span
                  className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <span
                  className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
              </span>
            )}
          </div>
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

      <div className="flex-shrink-0 w-10 h-10" />
    </div>
  );
};
