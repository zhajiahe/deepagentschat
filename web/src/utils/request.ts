import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

// 清除认证信息的函数
const clearAuthAndRedirect = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');

  // 使用 window.location.href 确保完全重定向
  const currentPath = window.location.pathname;
  if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
    window.location.href = '/web/login';
  }
};

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 检查 BaseResponse 格式的错误
    if (response.data && !response.data.success) {
      // 即使 HTTP 状态码是 200，但业务逻辑失败
      const error: any = new Error(response.data.msg || '请求失败');
      error.response = {
        data: response.data,
        status: response.data.code,
      };
      return Promise.reject(error);
    }
    return response;
  },
  async (error: AxiosError<any>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 如果是 401 或 403 错误（认证失败或权限不足）
    if (error.response?.status === 401 || error.response?.status === 403) {
      // 检查是否是 token 过期或无效
      const errorMsg = error.response?.data?.msg || '';
      const isAuthError =
        errorMsg.includes('token') ||
        errorMsg.includes('认证') ||
        errorMsg.includes('授权') ||
        errorMsg.includes('登录') ||
        error.response?.status === 401;

      if (isAuthError && !originalRequest._retry) {
        originalRequest._retry = true;

        // 尝试使用 refresh token 刷新
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          try {
            // TODO: 实现 refresh token 逻辑
            // const response = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
            // localStorage.setItem('access_token', response.data.access_token);
            // return request(originalRequest);

            // 目前直接清除认证并跳转
            clearAuthAndRedirect();
            return Promise.reject(error);
          } catch (refreshError) {
            // Refresh token 也失效，清除本地存储并跳转到登录页
            clearAuthAndRedirect();
            return Promise.reject(refreshError);
          }
        } else {
          // 没有 refresh token，直接清除并跳转
          clearAuthAndRedirect();
          return Promise.reject(error);
        }
      }
    }

    // 增强错误信息，从 BaseResponse 中提取 msg
    if (error.response?.data?.msg) {
      error.message = error.response.data.msg;
    }

    return Promise.reject(error);
  }
);

export default request;
