import { useCallback, useEffect } from 'react';
import type { ConversationCreate, ConversationResponse, ConversationUpdate, MessageResponse } from '@/api/aPIDoc';
import { useChatStore } from '@/stores/chatStore';
import request from '@/utils/request';

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
        setCurrentConversation(conversation);

        // 加载会话消息
        const response = await request.get(`/conversations/${conversation.thread_id}/messages`);
        // 解析 BaseResponse 包装的数据（现在返回 PageResponse 格式）
        if (response.data.success && response.data.data) {
          // 将 MessageResponse 转换为 Message 类型，并按创建时间排序（如果时间相同，则按ID排序）
          // 规范化角色：将 'ai' 映射为 'assistant' 以兼容旧数据
          const normalizeRole = (role: string): 'user' | 'assistant' | 'system' => {
            if (role === 'ai' || role === 'assistant') return 'assistant';
            if (role === 'human' || role === 'user') return 'user';
            return role as 'user' | 'assistant' | 'system';
          };
          // 从 PageResponse 中提取 items 数组
          const messageItems = response.data.data.items || response.data.data;
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
              // 如果时间相同，按ID排序（确保顺序稳定）
              return timeDiff !== 0 ? timeDiff : a.id - b.id;
            });
          setMessages(messages);
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
  }, [loadConversations]);

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
