import React from 'react';
import './DayGrid.css';

interface DayItem {
  date: string;
  dayName: string;
  entry?: {
    mood: number | null;
    has_media: boolean;
    health_score: number | null;
    sport_score: number | null;
    study_score: number | null;
    rest_score: number | null;
    comment: string | null;
    media_urls: (string | { type?: string; file_id?: string })[];
  };
}

interface Props {
  days: DayItem[];
  trackers: { id: number; name: string; icon: string }[];
  onDayClick: (date: string) => void;
}

const moodEmojis = ['😭', '😟', '😐', '🙂', '😄'];

function getAvgScore(entry: DayItem['entry']): number | null {
  if (!entry) return null;
  const scores = [entry.health_score, entry.sport_score, entry.study_score, entry.rest_score].filter(
    (s): s is number => s !== null && s !== undefined
  );
  if (scores.length === 0) return null;
  return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
}

export const DayGrid: React.FC<Props> = ({ days, onDayClick }) => {
  return (
    <div className="day-grid">
      {days.map((d) => {
        const avg = getAvgScore(d.entry);
        const hasJournal = avg !== null;
        const hasMood = !!d.entry?.mood;
        const hasMedia = d.entry?.has_media || (d.entry?.media_urls && d.entry.media_urls.length > 0);
        const hasComment = !!d.entry?.comment;

        return (
          <div key={d.date} className="day-cell" onClick={() => onDayClick(d.date)}>
            <div className="day-name">{d.dayName}</div>
            <div className="day-mood">
              {hasMood
                ? moodEmojis[d.entry!.mood! - 1]
                : hasJournal
                ? moodEmojis[avg! - 1] || '✅'
                : '◻️'}
            </div>
            <div className="day-badges">
              {hasMedia && <span className="badge media">📎</span>}
              {hasComment && <span className="badge comment">💬</span>}
              {hasJournal && !hasMood && <span className="badge journal">🤖</span>}
            </div>
          </div>
        );
      })}
    </div>
  );
};
