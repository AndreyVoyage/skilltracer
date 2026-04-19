import { useState } from 'react';

export function SetupScreen() {
  const [userId, setUserId] = useState('');
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    if (userId.trim()) {
      localStorage.setItem('st_user_id', userId.trim());
      localStorage.setItem('st_user_source', 'manual');
      setSaved(true);
      setTimeout(() => window.location.reload(), 600);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <div
        style={{
          background: 'white',
          borderRadius: '20px',
          padding: '32px',
          maxWidth: '360px',
          width: '100%',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
        <h1 style={{ margin: '0 0 8px', color: '#1a202c', fontSize: '24px' }}>
          Skill Tracer
        </h1>
        <p style={{ margin: '0 0 24px', color: '#718096', fontSize: '14px', lineHeight: 1.5 }}>
          Трекер навыков через Telegram
        </p>

        {saved ? (
          <div style={{ color: '#22c55e', fontWeight: 'bold' }}>
            ✅ Сохранено! Перезагрузка...
          </div>
        ) : (
          <>
            <div
              style={{
                background: '#fffbeb',
                border: '1px solid #f59e0b',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '20px',
                fontSize: '13px',
                color: '#92400e',
                textAlign: 'left',
              }}
            >
              <strong>⚠️ Первый вход</strong>
              <br />
              Введите ваш Telegram ID. Его можно узнать у бота{' '}
              <a href="https://t.me/userinfobot" style={{ color: '#2563eb' }}>
                @userinfobot
              </a>
            </div>

            <input
              type="number"
              placeholder="Ваш Telegram ID"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={{
                width: '100%',
                padding: '12px 16px',
                fontSize: '16px',
                border: '2px solid #e2e8f0',
                borderRadius: '12px',
                marginBottom: '12px',
                boxSizing: 'border-box',
                outline: 'none',
              }}
              onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            />

            <button
              onClick={handleSave}
              disabled={!userId.trim()}
              style={{
                width: '100%',
                padding: '14px',
                fontSize: '16px',
                fontWeight: 'bold',
                background: userId.trim() ? '#2481cc' : '#cbd5e0',
                color: 'white',
                border: 'none',
                borderRadius: '12px',
                cursor: userId.trim() ? 'pointer' : 'not-allowed',
                transition: 'background 0.2s',
              }}
            >
              🚀 Начать
            </button>

            <div style={{ marginTop: '16px', fontSize: '12px', color: '#a0aec0' }}>
              Или откройте через{' '}
              <a href="https://t.me/SkillTracer_bot" style={{ color: '#2481cc' }}>
                @SkillTracer_bot
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
