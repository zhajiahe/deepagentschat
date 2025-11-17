import { useState, useCallback } from 'react';
import { useChatStore } from '@/stores/chatStore';
import request from '@/utils/request';
import { ChatRequest, MessageResponse } from '@/api/aPIDoc';

export const useChat = () => {
  const {
    currentConversation,
    messages,
    addMessage,
    updateMessage,
    setIsSending,
    isSending,
  } = useChatStore();

  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null);
  const abortControllerRef = useState<{ current: AbortController | null }>({ current: null })[0];

  // 发送消息（流式）
  const sendMessageStream = useCallback(
    async (content: string, onNewConversation?: (threadId: string) => void) => {
      if (!content.trim() || isSending) return;

      setIsSending(true);

      // 添加用户消息
      const userMessageTime = new Date().toISOString();
      const userMessage = {
        id: Date.now(),
        role: 'user' as const,
        content,
        created_at: userMessageTime,
      };
      addMessage(userMessage);

      // 创建一个临时的助手消息用于流式更新
      // 确保助手消息的时间戳晚于用户消息
      const assistantMessageId = Date.now() + 1;
      const assistantMessageTime = new Date(Date.now() + 1).toISOString();
      const assistantMessage = {
        id: assistantMessageId,
        role: 'assistant' as const,
        content: '',
        created_at: assistantMessageTime,
        isStreaming: true,
      };
      addMessage(assistantMessage);
      setStreamingMessageId(assistantMessageId);

      try {
        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        const requestData: ChatRequest = {
          message: content,
          thread_id: currentConversation?.thread_id || null,
        };

        const response = await fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('access_token')}`,
          },
          body: JSON.stringify(requestData),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error('Stream request failed');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = '';
        let streamDone = false;
        const toolCalls: any[] = [];
        const toolCallsMap = new Map<string, any>();
        let newThreadId: string | null = null;

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                  continue;
                }
                try {
                  const parsed = JSON.parse(data);

                  // 捕获 thread_id（用于新会话）
                  if (parsed.thread_id && !currentConversation) {
                    newThreadId = parsed.thread_id;
                  }

                  // 处理不同类型的事件
                  if (parsed.type === 'content' && parsed.content) {
                    // LLM 内容流
                    accumulatedContent += parsed.content;
                    updateMessage(assistantMessageId, accumulatedContent);
                  } else if (parsed.type === 'tool_start') {
                    // 工具调用开始 - 创建临时工具调用记录
                    const toolCallId = `${parsed.tool_name}_${Date.now()}`;
                    const toolCall = {
                      name: parsed.tool_name,
                      input: parsed.tool_input,
                    };
                    toolCallsMap.set(toolCallId, toolCall);
                    toolCalls.push(toolCall);
                    // 更新消息的 metadata
                    const currentMessages = useChatStore.getState().messages;
                    const messageIndex = currentMessages.findIndex(m => m.id === assistantMessageId);
                    if (messageIndex !== -1) {
                      const updatedMessages = [...currentMessages];
                      updatedMessages[messageIndex] = {
                        ...updatedMessages[messageIndex],
                        metadata: {
                          ...updatedMessages[messageIndex].metadata,
                          tool_calls: [...toolCalls],
                        },
                      };
                      useChatStore.getState().setMessages(updatedMessages);
                    }
                  } else if (parsed.type === 'tool_end') {
                    // 工具调用结束 - 更新输出结果
                    const toolCall = toolCalls.find(tc => tc.name === parsed.tool_name);
                    if (toolCall) {
                      toolCall.output = parsed.tool_output;
                      // 更新消息的 metadata
                      const currentMessages = useChatStore.getState().messages;
                      const messageIndex = currentMessages.findIndex(m => m.id === assistantMessageId);
                      if (messageIndex !== -1) {
                        const updatedMessages = [...currentMessages];
                        updatedMessages[messageIndex] = {
                          ...updatedMessages[messageIndex],
                          metadata: {
                            ...updatedMessages[messageIndex].metadata,
                            tool_calls: [...toolCalls],
                          },
                        };
                        useChatStore.getState().setMessages(updatedMessages);
                      }
                    }
                  } else if (parsed.content) {
                    // 兼容旧格式（没有type字段）
                    accumulatedContent += parsed.content;
                    updateMessage(assistantMessageId, accumulatedContent);
                  }

                  // 检查是否完成
                  if (parsed.done) {
                    streamDone = true;
                  }

                  if (parsed.stopped) {
                    // 流式被停止
                    break;
                  }
                } catch (e) {
                  // 忽略解析错误，但记录日志以便调试
                  console.warn('Failed to parse SSE data:', data, e);
                }
              }
            }
          }
        }

        // 等待一小段时间确保后端保存完成
        if (streamDone) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }

        // 如果是新会话，通知父组件
        if (newThreadId && !currentConversation && onNewConversation) {
          onNewConversation(newThreadId);
        }

        // 流式完成后，重新加载消息以获取实际的数据库ID
        const targetThreadId = currentConversation?.thread_id || newThreadId;
        if (targetThreadId) {
          const messagesResponse = await request.get(
            `/conversations/${targetThreadId}/messages`
          );
          // 解析 BaseResponse 包装的数据（现在返回 PageResponse 格式）
          if (messagesResponse.data.success && messagesResponse.data.data) {
            const normalizeRole = (role: string): 'user' | 'assistant' | 'system' => {
              if (role === 'ai' || role === 'assistant') return 'assistant';
              if (role === 'human' || role === 'user') return 'user';
              return role as 'user' | 'assistant' | 'system';
            };
            // 从 PageResponse 中提取 items 数组
            const messageItems = messagesResponse.data.data.items || messagesResponse.data.data;
            const messages = messageItems
              .map((msg: MessageResponse) => ({
                id: msg.id,
                role: normalizeRole(msg.role),
                content: msg.content,
                created_at: msg.created_at,
                metadata: msg.metadata || {},
              }))
              .sort((a: any, b: any) => {
                const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                return timeDiff !== 0 ? timeDiff : a.id - b.id;
              });
            useChatStore.getState().setMessages(messages);
          }
        }

        setStreamingMessageId(null);
      } catch (error: any) {
        console.error('Failed to send message:', error);
        // 如果是用户主动取消，不显示错误消息
        if (error.name !== 'AbortError') {
          updateMessage(assistantMessageId, '抱歉，发送消息时出现错误。');
        }
        setStreamingMessageId(null);
      } finally {
        setIsSending(false);
        abortControllerRef.current = null;
      }
    },
    [currentConversation, isSending, addMessage, updateMessage, setIsSending, abortControllerRef]
  );

  // 发送消息（非流式）
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isSending) return;

      setIsSending(true);

      // 添加用户消息
      const userMessage = {
        id: Date.now(),
        role: 'user' as const,
        content,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);

      try {
        const requestData: ChatRequest = {
          message: content,
          thread_id: currentConversation?.thread_id || null,
        };

        const response = await request.post('/chat', requestData);

        // 解析 BaseResponse 包装的数据
        if (response.data.success && response.data.data) {
          const data = response.data.data;

          // 添加助手消息
          const assistantMessage = {
            id: Date.now() + 1,
            role: 'assistant' as const,
            content: data.response,
            created_at: new Date().toISOString(),
          };
          addMessage(assistantMessage);

          // 重新加载消息以获取实际的数据库ID
          if (data.thread_id) {
            const messagesResponse = await request.get(`/conversations/${data.thread_id}/messages`);
            if (messagesResponse.data.success && messagesResponse.data.data) {
              const normalizeRole = (role: string): 'user' | 'assistant' | 'system' => {
                if (role === 'ai' || role === 'assistant') return 'assistant';
                if (role === 'human' || role === 'user') return 'user';
                return role as 'user' | 'assistant' | 'system';
              };
              // 从 PageResponse 中提取 items 数组
              const messageItems = messagesResponse.data.data.items || messagesResponse.data.data;
              const messages = messageItems
                .map((msg: MessageResponse) => ({
                  id: msg.id,
                  role: normalizeRole(msg.role),
                  content: msg.content,
                  created_at: msg.created_at,
                  metadata: msg.metadata || {},
                }))
                .sort((a: any, b: any) => {
                  const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                  return timeDiff !== 0 ? timeDiff : a.id - b.id;
                });
              useChatStore.getState().setMessages(messages);
            }
          }
        }
      } catch (error) {
        console.error('Failed to send message:', error);
        const errorMessage = {
          id: Date.now() + 1,
          role: 'assistant' as const,
          content: '抱歉，发送消息时出现错误。',
          created_at: new Date().toISOString(),
        };
        addMessage(errorMessage);
      } finally {
        setIsSending(false);
      }
    },
    [currentConversation, isSending, addMessage, setIsSending]
  );

  // 停止流式响应
  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      // 中止 fetch 请求
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setStreamingMessageId(null);
      setIsSending(false);
    }
  }, [abortControllerRef, setIsSending]);

  return {
    messages,
    isSending,
    streamingMessageId,
    sendMessage,
    sendMessageStream,
    stopStreaming,
  };
};
