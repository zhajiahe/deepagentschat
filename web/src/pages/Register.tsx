import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { BaseResponseUserResponse, UserCreate } from '@/api/aPIDoc';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import request from '@/utils/request';

export const Register = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    username: '',
    email: '',
    nickname: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // 验证密码
    if (formData.password !== formData.confirmPassword) {
      toast({
        title: '验证失败',
        description: '两次输入的密码不一致',
        variant: 'destructive',
      });
      return;
    }

    if (formData.password.length < 6) {
      toast({
        title: '验证失败',
        description: '密码长度至少为 6 位',
        variant: 'destructive',
      });
      return;
    }

    setLoading(true);

    try {
      const userData: UserCreate = {
        username: formData.username,
        email: formData.email,
        nickname: formData.nickname,
        password: formData.password,
      };

      const response = await request.post<BaseResponseUserResponse>('/auth/register', userData);

      if (response.data.success) {
        toast({
          title: '注册成功',
          description: '请使用您的账号登录',
        });
        navigate('/login');
      } else {
        toast({
          title: '注册失败',
          description: response.data.msg || '注册失败',
          variant: 'destructive',
        });
      }
    } catch (err: any) {
      toast({
        title: '注册失败',
        description: err.response?.data?.msg || '注册失败，请稍后重试',
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
          <CardTitle className="text-2xl text-center">注册</CardTitle>
          <CardDescription className="text-center">创建新账号</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="username">用户名</Label>
              <Input
                id="username"
                name="username"
                type="text"
                required
                value={formData.username}
                onChange={handleChange}
                placeholder="请输入用户名（3-50个字符）"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange}
                placeholder="请输入邮箱"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="nickname">昵称</Label>
              <Input
                id="nickname"
                name="nickname"
                type="text"
                required
                value={formData.nickname}
                onChange={handleChange}
                placeholder="请输入昵称"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange}
                placeholder="请输入密码（至少6位）"
                disabled={loading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认密码</Label>
              <Input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="请再次输入密码"
                disabled={loading}
              />
            </div>

            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? '注册中...' : '注册'}
            </Button>

            <div className="text-center text-sm text-muted-foreground">
              <span>已有账号？</span>
              <Link to="/login" className="ml-1 text-primary hover:underline">
                立即登录
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
