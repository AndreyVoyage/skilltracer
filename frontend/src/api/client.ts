import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

function getUserIdFromInitData(initData: string): number | undefined {
  try {
    const params = new URLSearchParams(initData);
    const userJson = params.get('user');
    if (userJson) {
      const user = JSON.parse(userJson);
      if (user?.id) return user.id;
    }
  } catch {
    // ignore parse errors
  }
  return undefined;
}

function getEffectiveUserId(): string | null {
  const tg = (window as any).Telegram?.WebApp;

  // 1. Из initDataUnsafe (основной способ)
  if (tg?.initDataUnsafe?.user?.id) {
    const id = String(tg.initDataUnsafe.user.id);
    localStorage.setItem('st_user_id', id);
    localStorage.setItem('st_user_source', 'telegram');
    return id;
  }

  // 2. Из initData query string
  if (tg?.initData) {
    const numericId = getUserIdFromInitData(tg.initData);
    if (numericId) {
      const id = String(numericId);
      localStorage.setItem('st_user_id', id);
      return id;
    }
  }

  // 3. Из start_param (t.me/bot?startapp=xxx)
  const startParam = tg?.initDataUnsafe?.start_param;
  if (startParam) {
    localStorage.setItem('st_user_id', startParam);
    localStorage.setItem('st_user_source', 'start_param');
    return startParam;
  }

  // 4. Из localStorage (предыдущий вход)
  const cached = localStorage.getItem('st_user_id');
  if (cached) {
    // eslint-disable-next-line no-console
    console.log('[API Client] Using cached user_id:', cached);
    return cached;
  }

  // 5. Из URL параметра (для тестов)
  const urlParams = new URLSearchParams(window.location.search);
  const urlUserId = urlParams.get('user_id');
  if (urlUserId) {
    localStorage.setItem('st_user_id', urlUserId);
    return urlUserId;
  }

  return null;
}

api.interceptors.request.use((config) => {
  const tg = (window as any).Telegram?.WebApp;
  const initData = tg?.initData || '';
  const userId = getEffectiveUserId();

  if (initData) {
    // Стандартный способ через Telegram
    config.headers['X-Init-Data'] = initData;
  } else if (userId) {
    // Fallback для Android когда initData отсутствует
    config.params = config.params || {};
    if (!config.params.user_id) {
      config.params.user_id = userId;
    }
    // eslint-disable-next-line no-console
    console.log('[API Fallback] Using user_id:', userId);
  }

  // eslint-disable-next-line no-console
  console.log('[API Client] initData present:', !!initData, 'userId:', userId);

  return config;
});

// Response interceptor — сохраняем user_id если сервер его вернул
api.interceptors.response.use(
  (response) => {
    if (response.data?.user?.id) {
      localStorage.setItem('st_user_id', String(response.data.user.id));
    }
    return response;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
