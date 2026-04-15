import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { EntryForm } from '../components/EntryForm';
import { useEntries } from '../hooks/useEntries';
import api from '../api/client';
import './DayDetail.css';

export const DayDetail: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const { data, loading, error } = useEntries(date);
  const [saving, setSaving] = useState(false);

  if (loading) {
    return (
      <Layout>
        <div className="loading">Загрузка...</div>
      </Layout>
    );
  }

  if (error || !data || !date) {
    return (
      <Layout>
        <div className="error">Ошибка загрузки</div>
      </Layout>
    );
  }

  const entry = data.entries.find((e) => e.entry_date === date);
  const initialValues: Record<number, number> = {};
  entry?.metrics.forEach((m) => {
    initialValues[m.tracker_id] = m.value;
  });

  const handleSave = async (
    values: Record<number, number>,
    comment: string,
    mood: number
  ) => {
    setSaving(true);
    try {
      const metrics = Object.entries(values).map(([tracker_id, value]) => ({
        tracker_id: Number(tracker_id),
        value,
      }));
      await api.post('/entries', {
        entry_date: date,
        mood,
        text: comment,
        metrics,
      });
      navigate('/');
    } catch (e) {
      alert('Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <div className="day-detail-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Назад</button>
        <h2>{date}</h2>
      </div>

      {entry?.photo_file_id && (
        <img
          className="day-media"
          src={`/api/media/${entry.photo_file_id}`}
          alt="day"
        />
      )}
      {entry?.voice_file_id && (
        <audio className="day-media" controls src={`/api/media/${entry.voice_file_id}`} />
      )}

      <div className="card">
        {saving ? (
          <div className="loading">Сохранение...</div>
        ) : (
          <EntryForm
            trackers={data.trackers}
            initialValues={initialValues}
            initialComment={entry?.text || ''}
            initialMood={entry?.mood}
            onSave={handleSave}
            onCancel={() => navigate('/')}
          />
        )}
      </div>
    </Layout>
  );
};
