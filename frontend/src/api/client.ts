import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const tg = (window as any).Telegram?.WebApp;
  const initData = tg?.initData || '';
  if (initData) {
    config.headers['X-Init-Data'] = initData;
  }
  // Fallback: добавляем user_id в query params для всех запросов
  const userId = tg?.initDataUnsafe?.user?.id;
  if (userId) {
    config.params = config.params || {};
    if (!config.params.user_id) {
      config.params.user_id = userId;
    }
  }
  return config;
});

export default api;
