import { useEffect, useState } from 'react';
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

  useEffect(() => {
    const target = date || new Date().toISOString().split('T')[0];
    const d = new Date(target);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    const monday = new Date(d.setDate(diff));
    const start = monday.toISOString().split('T')[0];

    api
      .get('/entries/week', { params: { start_date: start } })
      .then((res) => {
        setData(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [date]);

  return { data, loading, error };
}
