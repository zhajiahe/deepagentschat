import { CheckIcon, CopyIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import type { AssistantMessage } from '@/stores/chatStore';
import { formatTime } from '@/utils/date';

interface AIMessageProps {
  message: AssistantMessage & { role: 'assistant' };
  onCopy: (content: string, id: number) => void;
  copiedId: number | null;
}

export const AIMessage = ({ message, onCopy, copiedId }: AIMessageProps) => {
  return (
    <div className="max-w-3xl w-full mx-auto px-4 animate-slide-up">
      <div className="bg-muted dark:bg-grokgray rounded-grok px-5 py-4 text-foreground dark:text-groktext">
        <div className="prose prose-base max-w-none dark:prose-invert prose-pre:bg-gray-900 prose-pre:text-gray-100 w-full">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
            {message.content}
          </ReactMarkdown>
          {message.isStreaming && (
            <span className="inline-flex gap-1 ml-2 items-center">
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          )}
        </div>

        {!message.isStreaming && (
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-border dark:border-grokborder">
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
              <span className="text-xs text-muted-foreground dark:text-groksub ml-auto" title={message.created_at}>
                {formatTime(message.created_at)}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
