import React from 'react';
import './DayGrid.css';

interface DayItem {
  date: string;
  dayName: string;
  entry?: {
    mood: number | null;
    has_media: boolean;
  };
}

interface Props {
  days: DayItem[];
  trackers: { id: number; name: string; icon: string }[];
  onDayClick: (date: string) => void;
}

const moodEmojis = ['😭', '😟', '😐', '🙂', '😄'];

export const DayGrid: React.FC<Props> = ({ days, onDayClick }) => {
  return (
    <div className="day-grid">
      {days.map((d) => (
        <div key={d.date} className="day-cell" onClick={() => onDayClick(d.date)}>
          <div className="day-name">{d.dayName}</div>
          <div className="day-mood">
            {d.entry?.mood ? moodEmojis[d.entry.mood - 1] : '◻️'}
          </div>
          {d.entry?.has_media && <div className="media-badge">📎</div>}
        </div>
      ))}
    </div>
  );
};
