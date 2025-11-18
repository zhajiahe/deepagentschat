import { create } from 'zustand';
import type { UserResponse } from '@/api/aPIDoc';
import { storage } from '@/utils/storage';

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  isAuthenticated: boolean;

  // Actions
  setAuth: (user: UserResponse, token: string, refreshToken: string) => void;
  clearAuth: () => void;
  logout: () => void;
  updateUser: (user: UserResponse) => void;
  initAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,

  setAuth: (user, token, refreshToken) => {
    storage.setToken(token);
    storage.setRefreshToken(refreshToken);
    storage.setUser(user);
    set({ user, token, isAuthenticated: true });
  },

  clearAuth: () => {
    storage.clearAuth();
    set({ user: null, token: null, isAuthenticated: false });
  },

  logout: () => {
    storage.clearAuth();
    set({ user: null, token: null, isAuthenticated: false });
    // 跳转到登录页
    window.location.href = '/web/login';
  },

  updateUser: (user) => {
    storage.setUser(user);
    set({ user });
  },

  initAuth: () => {
    const token = storage.getToken();
    const user = storage.getUser();
    if (token && user) {
      set({ user, token, isAuthenticated: true });
    }
  },
}));
