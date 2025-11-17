import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import request from '@/utils/request';
import { UserSettingsResponse, UserSettingsUpdate, PasswordChange } from '@/api/aPIDoc';
import { ArrowLeftIcon, SaveIcon } from 'lucide-react';
import { UserStats } from '@/components/UserStats';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Separator } from '@/components/ui/separator';

export const Settings = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { toast } = useToast();

  const [settings, setSettings] = useState<UserSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // 表单数据
  const [formData, setFormData] = useState({
    default_model: '',
    default_temperature: 0.7,
    default_max_tokens: 2000,
    theme: 'light',
    language: 'zh-CN',
  });

  // 密码修改
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    loadSettings();
    loadAvailableModels();
  }, [isAuthenticated, navigate]);

  const loadAvailableModels = async () => {
    try {
      setLoadingModels(true);
      const response = await request.get<any>('/users/models/available');
      if (response.data.success && response.data.data) {
        setAvailableModels(response.data.data);
      }
    } catch (err) {
      console.error('Failed to load available models:', err);
      // 静默失败，不影响其他设置的加载
    } finally {
      setLoadingModels(false);
    }
  };

  const loadSettings = async () => {
    try {
      setLoading(true);
      const response = await request.get<any>('/users/settings');
      if (response.data.success && response.data.data) {
        const data = response.data.data;
        setSettings(data);
        setFormData({
          default_model: data.default_model || '',
          default_temperature: data.default_temperature || 0.7,
          default_max_tokens: data.default_max_tokens || 2000,
          theme: data.theme || 'light',
          language: data.language || 'zh-CN',
        });
      }
    } catch (err) {
      console.error('Failed to load settings:', err);
      toast({
        title: '加载失败',
        description: '加载设置失败，请稍后重试',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);

      const currentSettings = settings?.settings || {};
      const updateData: UserSettingsUpdate = {
        default_model: formData.default_model || null,
        default_temperature: formData.default_temperature,
        default_max_tokens: formData.default_max_tokens,
        theme: formData.theme || null,
        language: formData.language || null,
        settings: currentSettings,
      };

      await request.put('/users/settings', updateData);
      toast({
        title: '保存成功',
        description: '设置已保存',
      });
      // 重新加载设置以更新本地状态
      await loadSettings();
    } catch (err: any) {
      toast({
        title: '保存失败',
        description: err.response?.data?.msg || '保存设置失败',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (passwordData.new_password !== passwordData.confirm_password) {
      toast({
        title: '验证失败',
        description: '两次输入的密码不一致',
        variant: 'destructive',
      });
      return;
    }

    if (passwordData.new_password.length < 6) {
      toast({
        title: '验证失败',
        description: '新密码长度至少为 6 位',
        variant: 'destructive',
      });
      return;
    }

    try {
      setSaving(true);
      const data: PasswordChange = {
        old_password: passwordData.old_password,
        new_password: passwordData.new_password,
      };
      await request.post('/auth/reset-password', data);
      toast({
        title: '修改成功',
        description: '密码已修改',
      });
      setPasswordData({ old_password: '', new_password: '', confirm_password: '' });
    } catch (err: any) {
      toast({
        title: '修改失败',
        description: err.response?.data?.msg || '修改密码失败',
        variant: 'destructive',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="max-w-4xl mx-auto px-4 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" asChild>
            <Link to="/chat">
              <ArrowLeftIcon size={20} className="mr-2" />
              返回聊天
            </Link>
          </Button>
          <h1 className="text-2xl font-bold">设置</h1>
        </div>

        {/* 用户统计 */}
        <UserStats />

        {/* 用户信息 */}
        <Card>
          <CardHeader>
            <CardTitle>用户信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-muted-foreground">用户名</Label>
              <div className="mt-1">{user?.username}</div>
            </div>
            <Separator />
            <div>
              <Label className="text-muted-foreground">昵称</Label>
              <div className="mt-1">{user?.nickname}</div>
            </div>
            <Separator />
            <div>
              <Label className="text-muted-foreground">邮箱</Label>
              <div className="mt-1">{user?.email}</div>
            </div>
          </CardContent>
        </Card>

        {/* AI 设置 */}
        <Card>
          <CardHeader>
            <CardTitle>AI 设置</CardTitle>
            <CardDescription>配置默认的 AI 模型参数</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="default_model">默认模型</Label>
              {loadingModels ? (
                <div className="text-sm text-muted-foreground">加载模型列表...</div>
              ) : availableModels.length > 0 ? (
                <Select
                  value={formData.default_model}
                  onValueChange={(value) => setFormData({ ...formData, default_model: value })}
                >
                  <SelectTrigger id="default_model">
                    <SelectValue placeholder="选择模型" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableModels.map((modelId) => (
                      <SelectItem key={modelId} value={modelId}>
                        {modelId}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id="default_model"
                  type="text"
                  value={formData.default_model}
                  onChange={(e) =>
                    setFormData({ ...formData, default_model: e.target.value })
                  }
                  placeholder="例如: Qwen/Qwen3-8B"
                />
              )}
              <p className="text-xs text-muted-foreground">
                选择您偏好的 AI 模型，将应用于所有新对话
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="temperature">
                温度 (Temperature): {formData.default_temperature}
              </Label>
              <input
                id="temperature"
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={formData.default_temperature}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    default_temperature: parseFloat(e.target.value),
                  })
                }
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>精确 (0)</span>
                <span>平衡 (1)</span>
                <span>创造 (2)</span>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_tokens">最大 Token 数</Label>
              <Input
                id="max_tokens"
                type="number"
                value={formData.default_max_tokens}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    default_max_tokens: parseInt(e.target.value),
                  })
                }
                min="100"
                max="8000"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="theme">主题</Label>
              <Select
                value={formData.theme}
                onValueChange={(value) => setFormData({ ...formData, theme: value })}
              >
                <SelectTrigger id="theme">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">亮色</SelectItem>
                  <SelectItem value="dark">暗色</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="language">语言</Label>
              <Select
                value={formData.language}
                onValueChange={(value) => setFormData({ ...formData, language: value })}
              >
                <SelectTrigger id="language">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="zh-CN">简体中文</SelectItem>
                  <SelectItem value="en-US">English</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleSaveSettings}
              disabled={saving}
              className="w-full"
            >
              <SaveIcon size={16} className="mr-2" />
              {saving ? '保存中...' : '保存设置'}
            </Button>
          </CardContent>
        </Card>

        {/* 修改密码 */}
        <Card>
          <CardHeader>
            <CardTitle>修改密码</CardTitle>
            <CardDescription>修改您的登录密码</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="old_password">当前密码</Label>
                <Input
                  id="old_password"
                  type="password"
                  value={passwordData.old_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, old_password: e.target.value })
                  }
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="new_password">新密码</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={passwordData.new_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, new_password: e.target.value })
                  }
                  required
                  minLength={6}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirm_password">确认新密码</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={passwordData.confirm_password}
                  onChange={(e) =>
                    setPasswordData({ ...passwordData, confirm_password: e.target.value })
                  }
                  required
                  minLength={6}
                />
              </div>

              <Button type="submit" disabled={saving} className="w-full">
                {saving ? '修改中...' : '修改密码'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
