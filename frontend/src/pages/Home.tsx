import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { DayGrid } from '../components/DayGrid';
import { TrackersList } from '../components/TrackersList';
import { useEntries } from '../hooks/useEntries';
import './Home.css';

const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const { data, loading, error } = useEntries();
  const [viewMode, setViewMode] = useState<'grid' | 'carousel'>('grid');

  if (loading) {
    return (
      <Layout>
        <div className="loading">Загрузка...</div>
      </Layout>
    );
  }

  if (error || !data) {
    return (
      <Layout>
        <div className="error">Ошибка загрузки данных</div>
      </Layout>
    );
  }

  const start = new Date(data.start_date);
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const iso = d.toISOString().split('T')[0];
    return {
      date: iso,
      dayName: dayNames[i],
      entry: data.entries.find((e) => e.entry_date === iso),
    };
  });

  return (
    <Layout>
      <div className="stats-row">
        <div className="stat-box">
          <div className="stat-number">{data.stats.filled_days}</div>
          <div className="stat-label">Дней</div>
        </div>
        <div className="stat-box">
          <div className="stat-number">{data.stats.avg_mood ?? '—'}</div>
          <div className="stat-label">Настроение</div>
        </div>
      </div>

      <div className="view-toggle">
        <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')}>
          Сетка
        </button>
        <button className={viewMode === 'carousel' ? 'active' : ''} onClick={() => setViewMode('carousel')}>
          Карусель
        </button>
      </div>

      {viewMode === 'grid' ? (
        <DayGrid days={days} trackers={data.trackers} onDayClick={(date) => navigate(`/day/${date}`)} />
      ) : (
        <div className="carousel-placeholder">
          {days.map((d) => (
            <div key={d.date} className="carousel-slide" onClick={() => navigate(`/day/${d.date}`)}>
              <div className="slide-day">{d.dayName}</div>
              <div className="slide-mood">
                {d.entry?.mood ? ['😭', '😟', '😐', '🙂', '😄'][d.entry.mood - 1] : '◻️'}
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="section-title">🏃 Трекеры</h2>
      <TrackersList trackers={data.trackers} onAdd={() => alert('Добавление трекера — через бота @SkillTracer_bot')} />
    </Layout>
  );
};
