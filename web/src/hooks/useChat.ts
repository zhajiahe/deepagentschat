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

  // 发送消息（流式）
  const sendMessageStream = useCallback(
    async (content: string) => {
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
        });

        if (!response.ok) {
          throw new Error('Stream request failed');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = '';

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

                  // 处理不同类型的事件
                  if (parsed.type === 'content' && parsed.content) {
                    // LLM 内容流
                    accumulatedContent += parsed.content;
                    updateMessage(assistantMessageId, accumulatedContent);
                  } else if (parsed.type === 'tool_start') {
                    // 工具调用开始
                    const toolInfo = `\n\n🔧 **调用工具**: ${parsed.tool_name}\n📥 **输入**: ${JSON.stringify(parsed.tool_input, null, 2)}\n`;
                    accumulatedContent += toolInfo;
                    updateMessage(assistantMessageId, accumulatedContent);
                  } else if (parsed.type === 'tool_end') {
                    // 工具调用结束
                    const toolResult = `\n✅ **结果**: ${parsed.tool_output}\n\n`;
                    accumulatedContent += toolResult;
                    updateMessage(assistantMessageId, accumulatedContent);
                  } else if (parsed.content) {
                    // 兼容旧格式（没有type字段）
                    accumulatedContent += parsed.content;
                    updateMessage(assistantMessageId, accumulatedContent);
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

        // 流式完成后，重新加载消息以获取实际的数据库ID
        if (currentConversation?.thread_id) {
          const messagesResponse = await request.get(
            `/conversations/${currentConversation.thread_id}/messages`
          );
          // 解析 BaseResponse 包装的数据
          if (messagesResponse.data.success && messagesResponse.data.data) {
            const normalizeRole = (role: string): 'user' | 'assistant' | 'system' => {
              if (role === 'ai' || role === 'assistant') return 'assistant';
              if (role === 'human' || role === 'user') return 'user';
              return role as 'user' | 'assistant' | 'system';
            };
            const messages = messagesResponse.data.data
              .map((msg: MessageResponse) => ({
                id: msg.id,
                role: normalizeRole(msg.role),
                content: msg.content,
                created_at: msg.created_at,
              }))
              .sort((a: any, b: any) => {
                const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                return timeDiff !== 0 ? timeDiff : a.id - b.id;
              });
            useChatStore.getState().setMessages(messages);
          }
        }

        setStreamingMessageId(null);
      } catch (error) {
        console.error('Failed to send message:', error);
        updateMessage(assistantMessageId, '抱歉，发送消息时出现错误。');
        setStreamingMessageId(null);
      } finally {
        setIsSending(false);
      }
    },
    [currentConversation, isSending, addMessage, updateMessage, setIsSending]
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
              const messages = messagesResponse.data.data
                .map((msg: MessageResponse) => ({
                  id: msg.id,
                  role: normalizeRole(msg.role),
                  content: msg.content,
                  created_at: msg.created_at,
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
  const stopStreaming = useCallback(async () => {
    if (!currentConversation?.thread_id) return;

    try {
      await request.post('/chat/stop', {
        thread_id: currentConversation.thread_id,
      });
      setStreamingMessageId(null);
      setIsSending(false);
    } catch (error) {
      console.error('Failed to stop streaming:', error);
    }
  }, [currentConversation, setIsSending]);

  return {
    messages,
    isSending,
    streamingMessageId,
    sendMessage,
    sendMessageStream,
    stopStreaming,
  };
};
