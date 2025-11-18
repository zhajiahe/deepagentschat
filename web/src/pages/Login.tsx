import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { BaseResponseToken } from '@/api/aPIDoc';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/stores/authStore';
import request from '@/utils/request';

export const Login = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);
  const { toast } = useToast();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await request.post<BaseResponseToken>('/auth/login', null, {
        params: { username, password },
      });

      if (response.data.success && response.data.data) {
        const { id, nickname, access_token, refresh_token } = response.data.data;

        // 先保存 token，然后获取完整用户信息
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        const userResponse = await request.get('/auth/me');

        if (userResponse.data.success && userResponse.data.data) {
          setAuth(userResponse.data.data, access_token, refresh_token);
          toast({
            title: '登录成功',
            description: `欢迎回来，${userResponse.data.data.nickname || username}！`,
          });
          navigate('/chat');
        } else {
          toast({
            title: '登录失败',
            description: '获取用户信息失败',
            variant: 'destructive',
          });
        }
      } else {
        toast({
          title: '登录失败',
          description: response.data.msg || '登录失败',
          variant: 'destructive',
        });
      }
    } catch (err: any) {
      toast({
        title: '登录失败',
        description: err.response?.data?.msg || '登录失败，请检查用户名和密码',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl text-center">登录</CardTitle>
          <CardDescription className="text-center">登录到 AI Agent</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                disabled={loading}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '登录中...' : '登录'}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              <span>还没有账号？</span>
              <Link to="/register" className="ml-1 text-primary hover:underline">
                立即注册
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
