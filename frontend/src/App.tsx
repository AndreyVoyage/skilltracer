import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Home } from './pages/Home';
import { DayDetail } from './pages/DayDetail';
import { PublicReport } from './pages/PublicReport';
import { useTelegram } from './hooks/useTelegram';
import { DebugPanel } from './components/DebugPanel';
import { SetupScreen } from './components/SetupScreen';
import { useEffect, useState } from 'react';

function App() {
  useTelegram();
  const [needsSetup, setNeedsSetup] = useState(false);

  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;

    // Пробуем получить user_id из start_param (t.me/bot?startapp=xxx)
    const initDataUnsafe = tg?.initDataUnsafe;
    if (initDataUnsafe?.start_param) {
      const userId = initDataUnsafe.start_param;
      localStorage.setItem('st_user_id', userId);
      localStorage.setItem('st_user_source', 'start_param');
      // eslint-disable-next-line no-console
      console.log('[App] Got user_id from start_param:', userId);
    }

    // Пробуем получить из initDataUnsafe.user.id
    if (initDataUnsafe?.user?.id) {
      const userId = String(initDataUnsafe.user.id);
      localStorage.setItem('st_user_id', userId);
      localStorage.setItem('st_user_source', 'telegram');
    }

    // Проверяем, нужен ли setup экран
    const cachedId = localStorage.getItem('st_user_id');
    if (!tg && !cachedId) {
      setNeedsSetup(true);
    }
  }, []);

  if (needsSetup) {
    return (
      <>
        <DebugPanel />
        <SetupScreen />
      </>
    );
  }

  return (
    <>
      <DebugPanel />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/day/:date" element={<DayDetail />} />
          <Route path="/report/:token" element={<PublicReport />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
