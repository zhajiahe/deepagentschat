import { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { Chat } from '@/pages/Chat';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { Settings } from '@/pages/Settings';
import { useAuthStore } from '@/stores/authStore';
import { useThemeStore } from '@/stores/themeStore';

function App() {
  const { initAuth, isAuthenticated } = useAuthStore();
  const initTheme = useThemeStore((state) => state.initTheme);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    initAuth();
    initTheme();
    setIsInitialized(true);
  }, [initAuth, initTheme]);

  // 等待初始化完成
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center h-screen bg-white dark:bg-gray-900">
        <div className="text-gray-600 dark:text-gray-400">加载中...</div>
      </div>
    );
  }

  return (
    <BrowserRouter basename="/web">
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/chat" element={isAuthenticated ? <Chat /> : <Navigate to="/login" replace />} />
        <Route path="/settings" element={isAuthenticated ? <Settings /> : <Navigate to="/login" replace />} />
        <Route
          path="/"
          element={isAuthenticated ? <Navigate to="/chat" replace /> : <Navigate to="/login" replace />}
        />
      </Routes>
      <Toaster />
    </BrowserRouter>
  );
}

export default App;
