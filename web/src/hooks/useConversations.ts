import { useCallback, useEffect } from 'react';
import type { ConversationCreate, ConversationResponse, ConversationUpdate, MessageResponse } from '@/api/aPIDoc';
import { useChatStore, type Message } from '@/stores/chatStore';
import request from '@/utils/request';

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

export const useConversations = () => {
  const {
    conversations,
    currentConversation,
    setConversations,
    addConversation,
    updateConversation,
    deleteConversation,
    setCurrentConversation,
    setMessages,
    setIsLoading,
  } = useChatStore();

  // 加载会话列表
  const loadConversations = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await request.get('/conversations');
      // 解析 BaseResponse 包装的分页数据
      if (response.data.success && response.data.data) {
        setConversations(response.data.data.items || []);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setIsLoading(false);
    }
  }, [setConversations, setIsLoading]);

  // 创建新会话
  const createConversation = useCallback(
    async (title?: string) => {
      try {
        const data: ConversationCreate = {
          title: title || '新对话',
        };
        const response = await request.post('/conversations', data);
        // 解析 BaseResponse 包装的数据
        if (response.data.success && response.data.data) {
          addConversation(response.data.data);
          setCurrentConversation(response.data.data);
          return response.data.data;
        }
        throw new Error(response.data.msg || '创建会话失败');
      } catch (error) {
        console.error('Failed to create conversation:', error);
        throw error;
      }
    },
    [addConversation, setCurrentConversation]
  );

  // 选择会话
  const selectConversation = useCallback(
    async (conversation: ConversationResponse) => {
      try {
        setIsLoading(true);

        // 加载会话消息
        const response = await request.get(`/conversations/${conversation.thread_id}/messages`, {
          params: { page_size: 1000 }, // 设置足够大的page_size以获取所有消息
        });
        // 解析 BaseResponse 包装的数据（现在返回 PageResponse 格式）
        if (response.data.success && response.data.data) {
          // 从 PageResponse 中提取 items 数组
          const messageItems = response.data.data.items || response.data.data;
          const messages = normalizeBackendMessages(messageItems);

          // 先设置消息，再设置当前会话，避免消息闪烁
          setMessages(messages);
          setCurrentConversation(conversation);
        }
      } catch (error) {
        console.error('Failed to load messages:', error);
      } finally {
        setIsLoading(false);
      }
    },
    [setCurrentConversation, setMessages, setIsLoading]
  );

  // 更新会话标题
  const updateConversationTitle = useCallback(
    async (threadId: string, title: string) => {
      try {
        const data: ConversationUpdate = { title };
        await request.patch(`/conversations/${threadId}`, data);
        updateConversation(threadId, { title });
      } catch (error) {
        console.error('Failed to update conversation:', error);
        throw error;
      }
    },
    [updateConversation]
  );

  // 删除会话
  const removeConversation = useCallback(
    async (threadId: string) => {
      try {
        await request.delete(`/conversations/${threadId}`);
        deleteConversation(threadId);
      } catch (error) {
        console.error('Failed to delete conversation:', error);
        throw error;
      }
    },
    [deleteConversation]
  );

  // 重置会话
  const resetConversation = useCallback(
    async (threadId: string) => {
      try {
        await request.post(`/conversations/${threadId}/reset`);
        setMessages([]);
      } catch (error) {
        console.error('Failed to reset conversation:', error);
        throw error;
      }
    },
    [setMessages]
  );

  // 初始化时加载会话列表
  useEffect(() => {
    loadConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    conversations,
    currentConversation,
    loadConversations,
    createConversation,
    selectConversation,
    updateConversationTitle,
    removeConversation,
    resetConversation,
  };
};
