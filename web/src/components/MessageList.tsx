import { useEffect, useRef, useState } from 'react';
import { MessageItem } from '@/components/MessageItem';
import { MessageSkeleton } from '@/components/MessageSkeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/hooks/use-toast';
import { type Message, useChatStore } from '@/stores/chatStore';
import { useUserSettingsStore } from '@/stores/userSettingsStore';
import 'highlight.js/styles/github-dark.css';

interface MessageListProps {
  messages: Message[];
}

// 扩展消息类型以支持工具调用消息
interface ExpandedMessage extends Message {
  isToolCall?: boolean;
  toolCall?: {
    name: string;
    arguments?: any;
    input?: any;
    output?: any;
  };
}

export const MessageList = ({ messages }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const { toast } = useToast();
  const { settings } = useUserSettingsStore();
  const { isLoading } = useChatStore();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 将消息展开，将工具调用作为独立的消息项
  const expandedMessages: ExpandedMessage[] = [];
  messages.forEach((message) => {
    // 如果是 AI 消息且有工具调用，先显示工具调用
    if (
      (message.role === 'assistant' || message.role === 'ai') &&
      settings.show_tool_calls &&
      message.metadata?.tool_calls &&
      message.metadata.tool_calls.length > 0
    ) {
      // 添加工具调用消息
      message.metadata.tool_calls.forEach((toolCall, index) => {
        expandedMessages.push({
          ...message,
          id: message.id * 1000 + index, // 生成唯一 ID
          isToolCall: true,
          toolCall: toolCall,
        });
      });
    }
    // 然后添加原始消息
    expandedMessages.push(message);
  });

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

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
        {expandedMessages.map((message) => (
          <MessageItem
            key={message.id}
            message={message}
            onCopy={handleCopy}
            copiedId={copiedId}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>
    </ScrollArea>
  );
};
