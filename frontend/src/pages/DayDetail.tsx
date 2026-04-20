import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { EntryForm } from '../components/EntryForm';
import { MediaGallery } from '../components/MediaGallery';
import type { MediaItem } from '../components/MediaGallery';
import { useEntries } from '../hooks/useEntries';
import api from '../api/client';
import './DayDetail.css';

export const DayDetail: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const { data, loading, error, refetch } = useEntries(date);
  const [saving, setSaving] = useState(false);

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

  // Находим entry с нормализацией формата даты
  const entry = React.useMemo(() => {
    if (!data?.entries || !date) return undefined;
    const targetDate = date.split('T')[0];
    return data.entries.find((e) => {
      const entryDate = typeof e.entry_date === 'string' ? e.entry_date.split('T')[0] : String(e.entry_date);
      return entryDate === targetDate;
    });
  }, [data, date]);

  const allMedia: MediaItem[] = React.useMemo(() => {
    const result: MediaItem[] = [];
    const seenFileIds = new Set<string>();

    // Новый unified формат (media_files из DailyEntry + merged JournalEntry)
    if (entry?.media_files && entry.media_files.length > 0) {
      for (const item of entry.media_files) {
        if (item && item.file_id && !seenFileIds.has(item.file_id)) {
          result.push(item);
          seenFileIds.add(item.file_id);
        }
      }
    }

    // Legacy поля — добавляем всегда, если есть и ещё не в списке
    if (entry?.photo_file_id && !seenFileIds.has(entry.photo_file_id)) {
      result.push({ id: 'legacy-photo', type: 'photo', file_id: entry.photo_file_id });
      seenFileIds.add(entry.photo_file_id);
    }
    if (entry?.video_file_id && !seenFileIds.has(entry.video_file_id)) {
      result.push({ id: 'legacy-video', type: 'video', file_id: entry.video_file_id });
      seenFileIds.add(entry.video_file_id);
    }
    if (entry?.voice_file_id && !seenFileIds.has(entry.voice_file_id)) {
      result.push({ id: 'legacy-voice', type: 'voice', file_id: entry.voice_file_id });
      seenFileIds.add(entry.voice_file_id);
    }

    return result;
  }, [entry]);

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

  const initialValues: Record<number, number> = {};
  entry?.metrics.forEach((m) => {
    initialValues[m.tracker_id] = m.value;
  });

  return (
    <Layout>
      <div className="day-detail-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Назад</button>
        <h2>{date}</h2>
      </div>

      {/* Media Gallery */}
      {allMedia.length > 0 && entry && (
        <MediaGallery
          entryId={entry.id}
          mediaItems={allMedia}
          onDelete={refetch}
        />
      )}

      {/* Comment from journal */}
      {entry?.comment && (
        <div className="journal-comment">
          <strong>💬 Заметка:</strong>
          <p>{entry.comment}</p>
        </div>
      )}

      {/* Text note from legacy daily entry */}
      {entry?.text && !entry?.comment && (
        <div className="journal-comment">
          <strong>📝 Заметка:</strong>
          <p>{entry.text}</p>
        </div>
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
