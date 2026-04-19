import { useEffect, useState } from 'react';

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        initDataUnsafe: {
          user?: {
            id: number;
            first_name: string;
            last_name?: string;
            username?: string;
          };
          start_param?: string;
        };
        ready: () => void;
        expand: () => void;
        close: () => void;
        setHeaderColor: (color: string) => void;
        setBackgroundColor: (color: string) => void;
        platform: string;
        version: string;
        colorScheme: string;
        MainButton: {
          text: string;
          show: () => void;
          hide: () => void;
          onClick: (cb: () => void) => void;
          offClick: (cb: () => void) => void;
          enable: () => void;
          disable: () => void;
        };
      };
    };
  }
}

export function useTelegram() {
  const [user, setUser] = useState<any>(null);
  const [tg, setTg] = useState<any>(null);
  const [debug, setDebug] = useState<Record<string, any>>({});

  useEffect(() => {
    const telegram = window.Telegram?.WebApp;
    const cachedId = localStorage.getItem('st_user_id');

    setDebug({
      platform: telegram?.platform,
      initDataPresent: !!telegram?.initData,
      initDataLength: telegram?.initData?.length || 0,
      unsafeUserId: telegram?.initDataUnsafe?.user?.id,
      startParam: telegram?.initDataUnsafe?.start_param,
      localStorageId: cachedId,
      timestamp: new Date().toISOString(),
    });

    if (telegram) {
      telegram.ready();
      telegram.expand();
      setTg(telegram);
      setUser(telegram.initDataUnsafe?.user || null);
    }
  }, []);

  return {
    tg,
    user,
    debug,
    initData: tg?.initData || '',
    setMainButton: (text: string, onClick: () => void) => {
      if (!tg) return;
      tg.MainButton.text = text;
      tg.MainButton.onClick(onClick);
      tg.MainButton.show();
    },
    hideMainButton: () => {
      if (!tg) return;
      tg.MainButton.hide();
    },
  };
}
