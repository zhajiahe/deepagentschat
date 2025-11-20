import { useCallback, useRef, useState } from 'react';
import type { ChatRequest, MessageResponse } from '@/api/aPIDoc';
import {
  useChatStore,
  type Message,
  type UserMessage,
  type AssistantMessage,
  type ToolCallMessage,
} from '@/stores/chatStore';

/**
 * 聊天钩子 - 重构版
 *
 * 核心设计：
 * 1. 消息分为三种类型：UserMessage、AssistantMessage、ToolCallMessage
 * 2. 流式阶段严格按照后端事件创建和更新消息
 * 3. 不使用启发式判断，完全依赖后端事件类型
 */
export const useChat = () => {
  const { messages, addMessage, updateMessage, setIsSending, isSending, setMessages } = useChatStore();
  const { currentConversation } = useChatStore();

  const abortControllerRef = useRef<AbortController | null>(null);

  // 流式状态管理 - 使用 ref 而不是 state，避免异步更新问题
  const currentAssistantMessageIdRef = useRef<number | null>(null);
  const toolCallMessagesMap = useRef<Map<string, number>>(new Map()); // tool_call_id -> message_id
  const incompleteLine = useRef('');

  const sendMessageStream = useCallback(
    async (content: string, onNewConversation?: (threadId: string) => void) => {
      if (!content.trim() || isSending) return;

      setIsSending(true);

      // 添加用户消息
      const userMessage: UserMessage = {
        id: Date.now(),
        type: 'user',
        content,
        created_at: new Date().toISOString(),
      };
      addMessage(userMessage);

      // 重置流式状态
      currentAssistantMessageIdRef.current = null;
      toolCallMessagesMap.current.clear();
      incompleteLine.current = '';

      try {
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
        let newThreadId: string | null = null;
        let doneMessages: any[] | null = null;

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = (incompleteLine.current + chunk).split('\n');
            incompleteLine.current = lines.pop() || '';

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                  continue;
                }
                try {
                  const parsed = JSON.parse(data);

                  if (parsed.thread_id && !currentConversation) {
                    newThreadId = parsed.thread_id;
                  }


                  switch (parsed.type) {
                    case 'message_start':
                      // 创建新的 AI 消息
                      {
                        const newMessageId = Date.now() + Math.random();
                        const newAssistantMessage: AssistantMessage = {
                          id: newMessageId,
                          type: 'assistant',
                          content: '',
                          created_at: new Date().toISOString(),
                          isStreaming: true,
                        };
                        addMessage(newAssistantMessage);
                        currentAssistantMessageIdRef.current = newMessageId;
                      }
                      break;

                    case 'message_end':
                      // 标记当前 AI 消息为完成状态
                      if (currentAssistantMessageIdRef.current) {
                        updateMessage(currentAssistantMessageIdRef.current, { isStreaming: false });
                        currentAssistantMessageIdRef.current = null;
                      }
                      break;

                    case 'content':
                      if (parsed.content) {
                        if (parsed.node === 'model' && currentAssistantMessageIdRef.current) {
                          // 处理来自 model 节点的内容（AI 生成的文本）
                          const currentMsgs = useChatStore.getState().messages;
                          const currentMsg = currentMsgs.find((m) => m.id === currentAssistantMessageIdRef.current);
                          if (currentMsg && currentMsg.type === 'assistant') {
                            const newContent = currentMsg.content + parsed.content;
                            updateMessage(currentAssistantMessageIdRef.current, { content: newContent });
                          }
                        } else if (parsed.node === 'tools') {
                          // 处理来自 tools 节点的内容（工具输出）
                          // 将工具输出更新到最后一个工具调用消息中
                          const toolMessageIds = Array.from(toolCallMessagesMap.current.values());
                          if (toolMessageIds.length > 0) {
                            const lastToolMessageId = toolMessageIds[toolMessageIds.length - 1];
                            const currentMsgs = useChatStore.getState().messages;
                            const toolMsg = currentMsgs.find((m) => m.id === lastToolMessageId);
                            if (toolMsg && toolMsg.type === 'tool_call') {
                              updateMessage(lastToolMessageId, {
                                toolCall: {
                                  ...toolMsg.toolCall,
                                  output: parsed.content,
                                },
                              });
                            }
                          }
                        }
                      }
                      break;

                    case 'tool_start':
                      // 创建新的工具调用消息
                      if (parsed.tool_call_id && parsed.tool_name) {
                        const toolMessageId = Date.now() + Math.random();
                        const toolCallMessage: ToolCallMessage = {
                          id: toolMessageId,
                          type: 'tool_call',
                          created_at: new Date().toISOString(),
                          isStreaming: true,
                          toolCall: {
                            id: parsed.tool_call_id,
                            name: parsed.tool_name,
                          },
                        };
                        addMessage(toolCallMessage);
                        toolCallMessagesMap.current.set(parsed.tool_call_id, toolMessageId);
                      }
                      break;

                    case 'tool_input':
                      // 更新工具调用的输入参数
                      if (parsed.tool_call_id) {
                        const toolMessageId = toolCallMessagesMap.current.get(parsed.tool_call_id);
                        if (toolMessageId) {
                          const currentMsgs = useChatStore.getState().messages;
                          const toolMsg = currentMsgs.find((m) => m.id === toolMessageId);
                          if (toolMsg && toolMsg.type === 'tool_call') {
                            updateMessage(toolMessageId, {
                              toolCall: {
                                ...toolMsg.toolCall,
                                input: parsed.tool_input,
                              },
                            });
                          }
                        }
                      }
                      break;

                    case 'tool_end':
                      // 更新工具调用的输出结果
                      if (parsed.tool_call_id) {
                        const toolMessageId = toolCallMessagesMap.current.get(parsed.tool_call_id);
                        if (toolMessageId) {
                          const currentMsgs = useChatStore.getState().messages;
                          const toolMsg = currentMsgs.find((m) => m.id === toolMessageId);
                          if (toolMsg && toolMsg.type === 'tool_call') {
                            updateMessage(toolMessageId, {
                              toolCall: {
                                ...toolMsg.toolCall,
                                output: parsed.tool_output,
                              },
                              isStreaming: false,
                            });
                          }
                        }
                      }
                      break;

                    case 'done':
                      if (parsed.messages && Array.isArray(parsed.messages)) {
                        doneMessages = parsed.messages;
                      }
                      break;

                    case 'stopped':
                      // Stream stopped by user
                      break;

                    default:
                      // console.warn('Unknown SSE event type:', parsed.type, parsed);
                      break;
                  }
                } catch (e) {
                  console.warn('Failed to parse SSE data:', data, e);
                }
              }
            }
          }
        }

        // 如果是新会话，通知父组件
        if (newThreadId && !currentConversation && onNewConversation) {
          onNewConversation(newThreadId);
        }

        // 流式结束后，确保所有消息的 isStreaming 状态为 false
        if (currentAssistantMessageIdRef.current) {
          updateMessage(currentAssistantMessageIdRef.current, { isStreaming: false });
        }

        // 标记所有工具调用消息为完成状态，并删除空的 AI 消息
        const currentMsgs = useChatStore.getState().messages;
        const filteredMessages = currentMsgs.filter((msg) => {
          // 删除空的 AI 消息（没有内容的 assistant 消息）
          if (msg.type === 'assistant' && !msg.content.trim()) {
            return false;
          }
          return true;
        }).map((msg) => {
          // 标记所有消息为完成状态
          if (msg.isStreaming) {
            return { ...msg, isStreaming: false };
          }
          return msg;
        });
        setMessages(filteredMessages);

        // 流式结束后，用后端返回的完整消息替换前端消息
        const targetThreadId = currentConversation?.thread_id || newThreadId;
        if (targetThreadId && doneMessages && doneMessages.length > 0) {
          const normalizedMessages = normalizeBackendMessages(doneMessages);

          // 保留用户消息之前的历史消息
          let lastUserIndex = -1;
          for (let i = currentMsgs.length - 1; i >= 0; i--) {
            if (currentMsgs[i].type === 'user') {
              lastUserIndex = i;
              break;
            }
          }
          const previousMessages = lastUserIndex > 0 ? currentMsgs.slice(0, lastUserIndex) : [];

          setMessages([...previousMessages, ...normalizedMessages]);
        }
      } catch (error: any) {
        console.error('Failed to send message:', error);
        if (error.name !== 'AbortError') {
          // 添加错误消息
          const errorMessage: AssistantMessage = {
            id: Date.now() + 1,
            type: 'assistant',
            content: '抱歉，发送消息时出现错误。',
            created_at: new Date().toISOString(),
          };
          addMessage(errorMessage);
        }
      } finally {
        setIsSending(false);
        abortControllerRef.current = null;
        currentAssistantMessageIdRef.current = null;
        toolCallMessagesMap.current.clear();
        incompleteLine.current = '';
      }
    },
    [currentConversation, isSending, addMessage, updateMessage, setIsSending, setMessages]
  );

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;

      // 标记所有流式消息为完成状态
      const currentMsgs = useChatStore.getState().messages;
      const streamingMessages = currentMsgs.filter((m) => m.isStreaming);
      streamingMessages.forEach((msg) => {
        updateMessage(msg.id, { isStreaming: false });
      });

      setIsSending(false);
      currentAssistantMessageIdRef.current = null;
      toolCallMessagesMap.current.clear();
      incompleteLine.current = '';
    }
  }, [setIsSending, updateMessage]);

  return {
    messages,
    isSending,
    sendMessageStream,
    stopStreaming,
  };
};

/**
 * 将后端消息格式转换为前端消息格式
 */
function normalizeBackendMessages(backendMessages: any[]): Message[] {
  const messages: Message[] = [];

  // 按照 _order_index 排序
  const sortedMessages = [...backendMessages].sort((a, b) => {
    const timeDiff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    if (timeDiff === 0) {
      return (a.metadata?._order_index || 0) - (b.metadata?._order_index || 0);
    }
    return timeDiff;
  });

  for (const msg of sortedMessages) {
    const role = normalizeRole(msg.role);

    // 跳过 ToolMessage 类型（它们已经合并到 AI 消息的 tool_calls 中）
    if (msg.type === 'ToolMessage') {
      continue;
    }

    if (role === 'user') {
      messages.push({
        id: msg.id || Date.now() + Math.random(),
        type: 'user',
        content: msg.content || '',
        created_at: msg.created_at || new Date().toISOString(),
      });
    } else if (role === 'assistant') {
      // 如果有工具调用，先添加工具调用消息
      if (msg.metadata?.tool_calls && msg.metadata.tool_calls.length > 0) {
        for (const toolCall of msg.metadata.tool_calls) {
          messages.push({
            id: Date.now() + Math.random(),
            type: 'tool_call',
            created_at: msg.created_at || new Date().toISOString(),
            toolCall: {
              id: toolCall.id || '',
              name: toolCall.name || '',
              input: toolCall.input,
              output: toolCall.output,
            },
          });
        }
      }

      // 然后添加 AI 消息（如果有内容）
      if (msg.content && msg.content.trim()) {
        messages.push({
          id: msg.id || Date.now() + Math.random(),
          type: 'assistant',
          content: msg.content,
          created_at: msg.created_at || new Date().toISOString(),
        });
      }
    }
  }

  return messages;
}

function normalizeRole(role: string): 'user' | 'assistant' | 'system' {
  if (role === 'ai' || role === 'assistant') return 'assistant';
  if (role === 'human' || role === 'user') return 'user';
  return role as 'user' | 'assistant' | 'system';
}
