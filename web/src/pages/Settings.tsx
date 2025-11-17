import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import request from '@/utils/request';
import { UserSettingsResponse, UserSettingsUpdate, PasswordChange } from '@/api/aPIDoc';
import { ArrowLeftIcon, SaveIcon, Trash2Icon } from 'lucide-react';
import { UserStats } from '@/components/UserStats';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { Separator } from '@/components/ui/separator';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export const Settings = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();
  const { toast } = useToast();

  const [settings, setSettings] = useState<UserSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingConversations, setDeletingConversations] = useState(false);

  // 表单数据
  const [formData, setFormData] = useState({
    llm_model: '',
    max_tokens: 2000,
  });

  // 密码修改
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: '',
  });

  const loadAvailableModels = async () => {
    try {
      setLoadingModels(true);
      const response = await request.get<any>('/users/models/available');
      if (response.data.success && response.data.data) {
        // 处理返回的模型数据，可能是 ModelInfo[] 或 string[]
        const models = response.data.data;
        if (Array.isArray(models)) {
          // 如果是 ModelInfo 对象数组，提取 id 字段
          if (models.length > 0 && typeof models[0] === 'object' && 'id' in models[0]) {
            setAvailableModels(models.map((m: any) => m.id));
          } else {
            // 如果是字符串数组，直接使用
            setAvailableModels(models);
          }
        }
      }
    } catch (err) {
      console.error('Failed to load available models:', err);
      // 静默失败，不影响其他设置的加载
      setAvailableModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  const loadSettings = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const response = await request.get<any>('/users/settings');
      if (response.data.success && response.data.data) {
        const data = response.data.data;
        setSettings(data);
        setFormData({
          llm_model: data.llm_model || '',
          max_tokens: data.max_tokens || 2000,
        });
      }
    } catch (err: any) {
      console.error('Failed to load settings:', err);
      const errorMsg = err.response?.data?.msg || err.message || '加载设置失败，请稍后重试';
      setLoadError(errorMsg);
      toast({
        title: '加载失败',
        description: errorMsg,
        variant: 'destructive',
      });
      // 即使加载失败，也设置默认值以防止白屏
      setFormData({
        llm_model: '',
        max_tokens: 2000,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    loadSettings();
    loadAvailableModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, navigate]);

  const handleSaveSettings = async () => {
    try {
      setSaving(true);

      const updateData: UserSettingsUpdate = {
        llm_model: formData.llm_model || null,
        max_tokens: formData.max_tokens,
        settings: settings?.settings || {},
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

  const handleClearAllConversations = async () => {
    try {
      setDeletingConversations(true);
      const response = await request.delete<any>('/conversations/all', {
        params: { hard_delete: true },
      });

      if (response.data.success) {
        toast({
          title: '清除成功',
          description: response.data.msg || '所有对话已清除',
        });
      }
    } catch (err: any) {
      toast({
        title: '清除失败',
        description: err.response?.data?.msg || '清除对话失败',
        variant: 'destructive',
      });
    } finally {
      setDeletingConversations(false);
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

        {/* 错误提示 */}
        {loadError && (
          <Card className="border-destructive">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-destructive">
                <span className="font-semibold">加载错误:</span>
                <span>{loadError}</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  loadSettings();
                  loadAvailableModels();
                }}
                className="mt-4"
              >
                重试
              </Button>
            </CardContent>
          </Card>
        )}

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
              <Label htmlFor="llm_model">LLM 模型</Label>
              {loadingModels ? (
                <div className="text-sm text-muted-foreground">加载模型列表...</div>
              ) : availableModels.length > 0 ? (
                <Select
                  value={formData.llm_model}
                  onValueChange={(value) => setFormData({ ...formData, llm_model: value })}
                >
                  <SelectTrigger id="llm_model">
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
                  id="llm_model"
                  type="text"
                  value={formData.llm_model}
                  onChange={(e) =>
                    setFormData({ ...formData, llm_model: e.target.value })
                  }
                  placeholder="例如: Qwen/Qwen2.5-7B-Instruct"
                />
              )}
              <p className="text-xs text-muted-foreground">
                选择您偏好的 LLM 模型，将应用于所有新对话
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_tokens">最大 Token 数</Label>
              <Input
                id="max_tokens"
                type="number"
                value={formData.max_tokens}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_tokens: parseInt(e.target.value) || 2000,
                  })
                }
                min="100"
                max="32768"
              />
              <p className="text-xs text-muted-foreground">
                控制模型生成的最大长度（1-32768）
              </p>
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

        {/* 清除所有对话 */}
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">危险操作</CardTitle>
            <CardDescription>以下操作不可恢复，请谨慎操作</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <h3 className="text-sm font-semibold mb-2">清除所有对话</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  这将永久删除您的所有对话记录和消息，此操作不可恢复。
                </p>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="destructive"
                      disabled={deletingConversations}
                    >
                      <Trash2Icon size={16} className="mr-2" />
                      {deletingConversations ? '清除中...' : '清除所有对话'}
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>确认清除所有对话？</AlertDialogTitle>
                      <AlertDialogDescription>
                        此操作将永久删除您的所有对话记录和消息，包括所有历史会话。
                        <br />
                        <strong className="text-destructive">此操作不可恢复！</strong>
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>取消</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleClearAllConversations}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        确认清除
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
