import { create } from 'zustand';
import type { ConversationResponse } from '@/api/aPIDoc';

export interface ToolCall {
  id?: string;
  name: string;
  arguments?: string;
  input?: any;
  output?: any;
}

export interface Message {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  isStreaming?: boolean;
  metadata?: {
    tool_calls?: ToolCall[];
    [key: string]: any;
  };
}

interface ChatState {
  // 当前会话列表
  conversations: ConversationResponse[];

  // 当前选中的会话
  currentConversation: ConversationResponse | null;

  // 当前会话的消息列表
  messages: Message[];

  // 是否正在加载
  isLoading: boolean;

  // 是否正在发送消息
  isSending: boolean;

  // Actions
  setConversations: (conversations: ConversationResponse[]) => void;
  addConversation: (conversation: ConversationResponse) => void;
  updateConversation: (threadId: string, updates: Partial<ConversationResponse>) => void;
  deleteConversation: (threadId: string) => void;
  setCurrentConversation: (conversation: ConversationResponse | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  updateMessage: (messageId: number, content: string) => void;
  setIsLoading: (isLoading: boolean) => void;
  setIsSending: (isSending: boolean) => void;
  clearMessages: () => void;
  clearAllState: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  isSending: false,

  setConversations: (conversations) => set({ conversations }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),

  updateConversation: (threadId, updates) =>
    set((state) => ({
      conversations: state.conversations.map((conv) => (conv.thread_id === threadId ? { ...conv, ...updates } : conv)),
      currentConversation:
        state.currentConversation?.thread_id === threadId
          ? { ...state.currentConversation, ...updates }
          : state.currentConversation,
    })),

  deleteConversation: (threadId) =>
    set((state) => ({
      conversations: state.conversations.filter((conv) => conv.thread_id !== threadId),
      currentConversation: state.currentConversation?.thread_id === threadId ? null : state.currentConversation,
      messages: state.currentConversation?.thread_id === threadId ? [] : state.messages,
    })),

  setCurrentConversation: (conversation) => set({ currentConversation: conversation }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (messageId, content) =>
    set((state) => ({
      messages: state.messages.map((msg) => (msg.id === messageId ? { ...msg, content, isStreaming: false } : msg)),
    })),

  setIsLoading: (isLoading) => set({ isLoading }),

  setIsSending: (isSending) => set({ isSending }),

  clearMessages: () => set({ messages: [] }),

  clearAllState: () =>
    set({
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      isSending: false,
    }),
}));
