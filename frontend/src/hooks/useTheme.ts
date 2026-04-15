import { useEffect, useState } from 'react';
import api from '../api/client';

export function useTheme() {
  const [theme, setTheme] = useState<'cozy' | 'neon'>('cozy');

  useEffect(() => {
    const saved = localStorage.getItem('skilltracer-theme') as 'cozy' | 'neon';
    if (saved) {
      setTheme(saved);
      document.body.setAttribute('data-theme', saved === 'neon' ? 'neon' : '');
    }
  }, []);

  const applyTheme = (newTheme: 'cozy' | 'neon') => {
    setTheme(newTheme);
    localStorage.setItem('skilltracer-theme', newTheme);
    document.body.setAttribute('data-theme', newTheme === 'neon' ? 'neon' : '');
    const tg = window.Telegram?.WebApp;
    if (tg) {
      if (newTheme === 'neon') {
        tg.setHeaderColor('#0A0E27');
        tg.setBackgroundColor('#0A0E27');
      } else {
        tg.setHeaderColor('#F5F1E8');
        tg.setBackgroundColor('#F5F1E8');
      }
    }
  };

  const toggleTheme = async () => {
    const newTheme = theme === 'cozy' ? 'neon' : 'cozy';
    applyTheme(newTheme);
    try {
      await api.post('/me/theme', { theme: newTheme });
    } catch (e) {
      console.error('Failed to save theme', e);
    }
  };

  return { theme, toggleTheme, applyTheme };
}
