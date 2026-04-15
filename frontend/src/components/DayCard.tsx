import React from 'react';
import type { Entry, Tracker } from '../hooks/useEntries';
import './DayCard.css';

interface Props {
  date: string;
  dayName: string;
  entry?: Entry;
  trackers: Tracker[];
  onClick: () => void;
}

export const DayCard: React.FC<Props> = ({ date, dayName, entry, trackers, onClick }) => {
  const isFilled = !!entry;
  const moodEmoji = entry?.mood
    ? ['😭', '😟', '😐', '🙂', '😄'][entry.mood - 1] || '😐'
    : '—';

  return (
    <div className={`day-card ${isFilled ? 'filled' : ''}`} onClick={onClick}>
      <div className="day-header">
        <span className="day-name">{dayName}</span>
        <span className="day-date">{date.slice(8, 10)}.{date.slice(5, 7)}</span>
      </div>
      <div className="day-mood">{moodEmoji}</div>
      <div className="day-trackers">
        {trackers.slice(0, 4).map((t) => {
          const metric = entry?.metrics.find((m) => m.tracker_id === t.id);
          return (
            <span key={t.id} className={`tracker-dot ${metric ? 'has-value' : ''}`}>
              {t.icon}
            </span>
          );
        })}
      </div>
      {entry?.has_media && <div className="media-badge">📎</div>}
    </div>
  );
};
