import { useState, useEffect } from 'react';

export function DebugPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [apiStatus, setApiStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [manualId, setManualId] = useState('');
  const [showInput, setShowInput] = useState(false);

  const addLog = (msg: string) => {
    setLogs((prev) => [`${new Date().toLocaleTimeString()} ${msg}`, ...prev].slice(0, 15));
  };

  useEffect(() => {
    // Автотест при загрузке (тихий)
    const tg = (window as any).Telegram?.WebApp;
    const cachedId = localStorage.getItem('st_user_id');

    // eslint-disable-next-line no-console
    console.log('[SilentTest] Platform:', tg?.platform);
    // eslint-disable-next-line no-console
    console.log('[SilentTest] cachedId:', cachedId);

    if (!cachedId && !tg?.initData) {
      setApiStatus('error');
    } else {
      setApiStatus('ok');
    }
  }, []);

  const runFullTest = async () => {
    setIsOpen(true);
    setLogs(['🔍 Запуск диагностики...']);

    const tg = (window as any).Telegram?.WebApp;
    const cachedId = localStorage.getItem('st_user_id');

    addLog(`Platform: ${tg?.platform || 'NONE'}`);
    addLog(`Version: ${tg?.version || 'N/A'}`);
    addLog(`initData: ${tg?.initData ? 'YES' : 'NO'} (len:${tg?.initData?.length || 0})`);
    addLog(`initDataUnsafe.user: ${tg?.initDataUnsafe?.user?.id || 'NONE'}`);
    addLog(`localStorage.st_user_id: ${cachedId || 'NULL'}`);

    if (!cachedId && !tg?.initDataUnsafe?.user?.id) {
      setShowInput(true);
      addLog('⚠️ Нет user_id. Введите вручную:');
    }

    // Тест API
    try {
      const health = await fetch('/health').then((r) => r.json());
      addLog(`✅ Health: ${health.status}`);
    } catch (e: any) {
      addLog(`❌ Health: ${e.message}`);
    }

    // Тест с текущим ID
    const testId = tg?.initDataUnsafe?.user?.id || cachedId;
    if (testId) {
      try {
        const headers: Record<string, string> = {};
        if (tg?.initData) headers['X-Init-Data'] = tg.initData;

        const url = `/api/v1/entries/week?start_date=2026-04-13${!tg?.initData ? `&user_id=${testId}` : ''}`;
        addLog(`Testing: ${url.substring(0, 40)}...`);

        const resp = await fetch(url, { headers });
        setApiStatus(resp.ok ? 'ok' : 'error');
        addLog(`${resp.status === 200 ? '✅' : '❌'} API: ${resp.status}`);

        if (resp.ok) {
          const data = await resp.json();
          addLog(`Entries: ${data.entries?.length || 0}, Trackers: ${data.trackers?.length || 0}`);

          // Детальная информация о медиа
          if (data.entries && data.entries.length > 0) {
            const today = new Date().toISOString().split('T')[0];
            const todayEntry = data.entries.find((e: any) => e.entry_date === today);
            if (todayEntry) {
              addLog(`--- Детали медиа ---`);
              addLog(`Entry ID: ${todayEntry.id || 'N/A'}`);
              addLog(`Has media (флаг): ${todayEntry.has_media}`);

              // Новое поле media_files
              if (todayEntry.media_files && todayEntry.media_files.length > 0) {
                addLog(`✅ media_files (JSON): ${todayEntry.media_files.length} файлов`);
                todayEntry.media_files.forEach((m: any, i: number) => {
                  const hasDeleteId = m.id ? '✓' : '✗';
                  addLog(`  [${i}] ${hasDeleteId} ID:${m.id?.substring(0,8)||'NO_ID'} Type:${m.type} FileID:${m.file_id?.substring(0,15)}...`);
                });
              } else {
                addLog(`⚠️ media_files пустой или отсутствует`);
              }

              // Deprecated поля
              let deprecatedCount = 0;
              if (todayEntry.photo_file_id) {
                addLog(`❌ Deprecated: photo_file_id=${todayEntry.photo_file_id.substring(0,20)}...`);
                deprecatedCount++;
              }
              if (todayEntry.video_file_id) {
                addLog(`❌ Deprecated: video_file_id=${todayEntry.video_file_id.substring(0,20)}...`);
                deprecatedCount++;
              }
              if (todayEntry.voice_file_id) {
                addLog(`❌ Deprecated: voice_file_id=${todayEntry.voice_file_id.substring(0,20)}...`);
                deprecatedCount++;
              }

              // Итог
              if (todayEntry.media_files?.length > 0 && deprecatedCount === 0) {
                addLog(`✅ СИСТЕМА РАБОТАЕТ ПРАВИЛЬНО (APPEND)`);
              } else if (todayEntry.media_files?.length > 0 && deprecatedCount > 0) {
                addLog(`⚠️ СМЕШАННАЯ СИСТЕМА: Есть и новые и старые поля`);
              } else if (deprecatedCount > 0) {
                addLog(`❌ СТАРАЯ СИСТЕМА (REPLACE): Фото заменяются!`);
                addLog(`   Крестик удаления НЕДОСТУПЕН для старых фото`);
              } else {
                addLog(`ℹ️ Медиа нет в этой записи`);
              }
            } else {
              addLog(`⚠️ Запись за ${today} не найдена в ответе`);
            }
          }
        } else if (resp.status === 401) {
          addLog('⚠️ 401 - initData invalid или нет user_id');
        }
      } catch (e: any) {
        addLog(`❌ API Error: ${e.message}`);
        setApiStatus('error');
      }
    } else {
      addLog('❌ Нет user_id для теста');
      setApiStatus('error');
    }
  };

  const clearCache = () => {
    localStorage.removeItem('st_user_id');
    localStorage.removeItem('st_user_source');
    addLog('🗑 localStorage очищен');
    window.location.reload();
  };

  const copyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    addLog('📋 Скопировано в буфер');
  };

  return (
    <>
      {/* Минималистичная кнопка - всегда видна */}
      <button
        onClick={runFullTest}
        style={{
          position: 'fixed',
          top: '10px',
          right: '10px',
          zIndex: 10000,
          width: '32px',
          height: '32px',
          borderRadius: '50%',
          border: 'none',
          background: apiStatus === 'ok' ? '#22c55e' : apiStatus === 'error' ? '#ef4444' : '#f59e0b',
          color: 'white',
          fontSize: '16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          opacity: 0.9,
          cursor: 'pointer',
        }}
      >
        {apiStatus === 'ok' ? '✓' : apiStatus === 'error' ? '!' : '?'}
      </button>

      {/* Панель логов - только при открытии */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: '50px',
            right: '10px',
            left: '10px',
            maxHeight: '60vh',
            overflow: 'auto',
            background: 'rgba(0,0,0,0.95)',
            color: '#00ff00',
            padding: '15px',
            fontSize: '13px',
            fontFamily: 'monospace',
            zIndex: 9999,
            borderRadius: '12px',
            border: '2px solid #22c55e',
          }}
        >
          <div
            style={{
              color: '#fff',
              marginBottom: '10px',
              fontWeight: 'bold',
              display: 'flex',
              justifyContent: 'space-between',
            }}
          >
            <span>🔍 Debug Info</span>
            <span onClick={() => setIsOpen(false)} style={{ cursor: 'pointer' }}>
              ✕
            </span>
          </div>

          {logs.map((log, i) => (
            <div
              key={i}
              style={{
                marginBottom: '4px',
                wordBreak: 'break-all',
                color: log.includes('❌')
                  ? '#ff4444'
                  : log.includes('✅')
                  ? '#44ff44'
                  : '#ffff00',
                fontSize: '12px',
              }}
            >
              {log}
            </div>
          ))}

          {/* Форма ввода Telegram ID */}
          {showInput && (
            <div
              style={{
                margin: '15px 0',
                padding: '15px',
                background: '#333',
                borderRadius: '8px',
                border: '2px solid #f59e0b',
              }}
            >
              <div style={{ color: '#fff', marginBottom: '10px', fontSize: '14px' }}>
                🔑 Введите ваш Telegram ID:
              </div>
              <input
                type="number"
                value={manualId}
                onChange={(e) => setManualId(e.target.value)}
                placeholder="6072711152"
                style={{
                  width: '100%',
                  padding: '12px',
                  fontSize: '16px',
                  borderRadius: '6px',
                  border: '1px solid #666',
                  marginBottom: '10px',
                  background: '#222',
                  color: '#fff',
                  boxSizing: 'border-box',
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && manualId.length > 5) {
                    localStorage.setItem('st_user_id', manualId);
                    addLog(`✅ Сохранён ID: ${manualId}`);
                    setShowInput(false);
                    setTimeout(() => window.location.reload(), 800);
                  }
                }}
              />
              <button
                onClick={() => {
                  if (manualId && manualId.length > 5) {
                    localStorage.setItem('st_user_id', manualId);
                    addLog(`✅ Сохранён ID: ${manualId}`);
                    setShowInput(false);
                    setTimeout(() => window.location.reload(), 800);
                  } else {
                    addLog('❌ ID слишком короткий');
                  }
                }}
                style={{
                  width: '100%',
                  padding: '12px',
                  background: '#22c55e',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                💾 Сохранить и войти
              </button>
            </div>
          )}

          <div style={{ marginTop: '15px', display: 'flex', gap: '8px' }}>
            <button
              onClick={copyLogs}
              style={{
                flex: 1,
                padding: '8px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            >
              📋 Copy
            </button>
            <button
              onClick={clearCache}
              style={{
                flex: 1,
                padding: '8px',
                background: '#ef4444',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            >
              🗑 Clear
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{
                flex: 1,
                padding: '8px',
                background: '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
              }}
            >
              🔄 Reload
            </button>
          </div>
        </div>
      )}
    </>
  );
}
