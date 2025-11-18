import { BotIcon } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
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

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-background p-4 sm:p-6 md:p-8">
        <div className="text-center animate-fade-in max-w-2xl">
          <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-emerald-300 to-slate-400 rounded-full flex items-center justify-center mb-4 shadow-lg mx-auto">
            <BotIcon className="w-8 h-8 sm:w-10 sm:h-10 text-white" />
          </div>
          <h3 className="text-lg sm:text-xl font-semibold mb-2">开始新的对话</h3>
          <p className="text-sm text-muted-foreground px-4">输入消息开始与 AI 助手聊天</p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <div className="max-w-full sm:max-w-3xl md:max-w-4xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl mx-auto space-y-6">
          {expandedMessages.map((message) => (
            <div
              key={message.id}
              className="flex gap-4 items-start animate-slide-up"
              style={{ animationDelay: `${index * 0.05}s` }}
            >
              {/* 左侧头像区域 */}
              {message.role === 'assistant' || message.role === 'ai' || message.isToolCall ? (
                <Avatar className="flex-shrink-0 w-10 h-10 ring-2 ring-primary/20 shadow-md">
                  <AvatarFallback
                    className={
                      message.isToolCall
                        ? 'bg-gradient-to-br from-orange-500 to-red-600'
                        : 'bg-gradient-to-br from-emerald-400 to-slate-500'
                    }
                  >
                    {message.isToolCall ? '🔧' : <BotIcon size={20} className="text-white" />}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <div className="flex-shrink-0 w-10 h-10" />
              )}

              {/* 消息内容区域 */}
              <div className={`flex-1 ${message.role === 'user' ? 'flex justify-end' : ''}`}>
                <div className={message.role === 'user' ? 'max-w-[85%] sm:max-w-[80%] md:max-w-[75%]' : 'max-w-[90%]'}>
                  <div
                    className={`relative rounded-2xl px-4 py-3 shadow-md transition-all duration-200 hover:shadow-lg ${
                      message.role === 'user'
                        ? 'bg-gradient-to-br from-emerald-400 to-slate-500 text-white'
                        : message.isToolCall
                          ? 'bg-orange-50 dark:bg-orange-950/30 text-foreground border-2 border-orange-300 dark:border-orange-700'
                          : 'bg-muted/50 dark:bg-muted text-foreground border border-border'
                    }`}
                  >
                    {/* 工具调用消息 */}
                    {message.isToolCall && message.toolCall ? (
                      <div className="space-y-2">
                        <button
                          onClick={() => toggleToolCall(message.id)}
                          className="w-full flex items-center justify-between text-orange-700 dark:text-orange-400 font-semibold hover:opacity-80 transition-opacity"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-lg">🔧</span>
                            <span>调用工具: {message.toolCall.name}</span>
                          </div>
                          <span className="text-sm">{expandedToolCalls.has(message.id) ? '▼' : '▶'}</span>
                        </button>

                        {/* 简洁显示输入参数 */}
                        {!expandedToolCalls.has(message.id) &&
                          (message.toolCall.arguments || message.toolCall.input) && (
                            <div className="text-xs text-muted-foreground truncate">
                              {JSON.stringify(message.toolCall.arguments || message.toolCall.input)}
                            </div>
                          )}

                        {expandedToolCalls.has(message.id) && (
                          <div className="space-y-2 animate-slide-up">
                            {(message.toolCall.arguments || message.toolCall.input) && (
                              <div>
                                <div className="text-sm text-muted-foreground mb-1">输入参数：</div>
                                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                                  {JSON.stringify(message.toolCall.arguments || message.toolCall.input, null, 2)}
                                </pre>
                              </div>
                            )}
                            {message.toolCall.output && (
                              <div>
                                <div className="text-sm text-muted-foreground mb-1">输出结果：</div>
                                <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-40">
                                  {typeof message.toolCall.output === 'string'
                                    ? message.toolCall.output
                                    : JSON.stringify(message.toolCall.output, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ) : message.role === 'assistant' || message.role === 'ai' ? (
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
                    ) : (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    )}
                  </div>

                  {/* 操作按钮和时间戳 - 工具调用消息不显示 */}
                  {!message.isStreaming && !message.isToolCall && (
                    <div className="flex items-center justify-between gap-2 mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(message.content, message.id)}
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

              {/* 右侧头像区域 */}
              {message.role === 'user' ? (
                <Avatar className="flex-shrink-0 w-10 h-10 ring-2 ring-primary/20 shadow-md">
                  <AvatarFallback className="bg-gradient-to-br from-emerald-400 to-slate-500">
                    <UserIcon size={20} className="text-white" />
                  </AvatarFallback>
                </Avatar>
              ) : (
                <div className="flex-shrink-0 w-10 h-10" />
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </ScrollArea>
  );
};
