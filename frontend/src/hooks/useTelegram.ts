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
        };
        ready: () => void;
        expand: () => void;
        close: () => void;
        setHeaderColor: (color: string) => void;
        setBackgroundColor: (color: string) => void;
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

  useEffect(() => {
    const telegram = window.Telegram?.WebApp;
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
