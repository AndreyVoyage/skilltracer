import { useEffect, useState, useCallback } from 'react';
import api from '../api/client';

export interface Tracker {
  id: number;
  name: string;
  icon: string;
  is_default: boolean;
}

export interface Metric {
  tracker_id: number;
  value: number;
}

export interface MediaItem {
  id?: string;
  type?: string;
  file_id?: string;
  caption?: string | null;
  created_at?: string;
}

export interface Entry {
  id: number;
  entry_date: string;
  mood: number | null;
  text: string | null;
  photo_file_id: string | null;
  voice_file_id: string | null;
  video_file_id: string | null;
  has_media: boolean;
  metrics: Metric[];
  // Unified media array (DailyEntry.media_files + JournalEntry.media_urls merged)
  media_files: MediaItem[];
  // Bot journal fields
  health_score: number | null;
  sport_score: number | null;
  study_score: number | null;
  rest_score: number | null;
  comment: string | null;
  media_urls: (string | { type?: string; file_id?: string })[];  // Deprecated
}

export interface WeekData {
  start_date: string;
  entries: Entry[];
  trackers: Tracker[];
  stats: {
    filled_days: number;
    avg_mood: number | null;
  };
}

export function useEntries(date?: string) {
  const [data, setData] = useState<WeekData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchData = useCallback(() => {
    const target = date || new Date().toISOString().split('T')[0];
    const d = new Date(target);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(d.setDate(diff));
    const start = monday.toISOString().split('T')[0];

    setLoading(true);
    setError(false);

    api
      .get('/entries/week', { params: { start_date: start } })
      .then((res) => {
        // eslint-disable-next-line no-console
        console.log('[useEntries] response:', res.data);
        setData(res.data);
        setLoading(false);
      })
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.error('[useEntries] error:', err.response?.status, err.response?.data);
        setError(true);
        setLoading(false);
      });
  }, [date]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
