import { useEffect, useState } from 'react';
import request from '@/utils/request';

interface UserSettings {
  show_tool_calls: boolean;
}

export const useUserSettings = () => {
  const [settings, setSettings] = useState<UserSettings>({
    show_tool_calls: true, // 默认值
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const loadSettings = async () => {
    try {
      const response = await request.get<any>('/users/settings');
      if (response.data.success && response.data.data) {
        const data = response.data.data;
        const settingsJson = data.settings || {};
        setSettings({
          show_tool_calls: settingsJson.show_tool_calls !== undefined ? settingsJson.show_tool_calls : true,
        });
      }
    } catch (err) {
      console.error('Failed to load user settings:', err);
      // 使用默认值
    } finally {
      setLoading(false);
    }
  };

  return {
    settings,
    loading,
    refreshSettings: loadSettings,
  };
};
