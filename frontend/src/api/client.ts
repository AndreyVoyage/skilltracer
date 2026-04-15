import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const initData = (window as any).Telegram?.WebApp?.initData || '';
  if (initData) {
    config.headers.Authorization = `tma ${initData}`;
  }
  return config;
});

export default api;
