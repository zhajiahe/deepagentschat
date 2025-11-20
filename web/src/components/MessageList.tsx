import { useEffect, useRef, useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { useChatStore, type Message } from '@/stores/chatStore';
import { MessageSkeleton } from './MessageSkeleton';
import { UserMessage } from './UserMessage';
import { AIMessage } from './AIMessage';
import { ToolCallMessage } from './ToolCallMessage';

interface MessageListProps {
  messages: Message[];
}

export const MessageList = ({ messages }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const { toast } = useToast();
  const { isLoading } = useChatStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleCopy = (content: string, id: number) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    toast({
      title: '已复制',
      description: '消息内容已复制到剪贴板',
    });
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Show loading skeleton when loading messages
  if (isLoading && messages.length === 0) {
    return (
      <ScrollArea className="flex-1">
        <div className="max-w-full sm:max-w-3xl md:max-w-4xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl mx-auto">
          <MessageSkeleton />
        </div>
      </ScrollArea>
    );
  }

  return (
    <ScrollArea className="flex-1 bg-background dark:bg-grokbg">
      <div className="py-6 space-y-6">
        {messages.map((message) => {
          switch (message.type) {
            case 'user':
              return (
                <UserMessage
                  key={message.id}
                  message={{ ...message, role: 'user' }}
                  onCopy={handleCopy}
                  copiedId={copiedId}
                />
              );
            case 'assistant':
              return (
                <AIMessage
                  key={message.id}
                  message={{ ...message, role: 'assistant' }}
                  onCopy={handleCopy}
                  copiedId={copiedId}
                />
              );
            case 'tool_call':
              return (
                <div key={message.id} className="max-w-3xl w-full mx-auto px-4 animate-slide-up">
                  <div className="bg-orange-50 dark:bg-orange-950/30 rounded-grok px-5 py-4 text-foreground border border-orange-300 dark:border-orange-700">
                    <ToolCallMessage toolCall={message.toolCall} messageId={message.id} isStreaming={message.isStreaming} />
                  </div>
                </div>
              );
            default:
              return null;
          }
        })}
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
};
