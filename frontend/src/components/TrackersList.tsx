import React from 'react';
import type { Tracker } from '../hooks/useEntries';
import './TrackersList.css';

interface Props {
  trackers: Tracker[];
  onAdd: () => void;
}

export const TrackersList: React.FC<Props> = ({ trackers, onAdd }) => {
  return (
    <div className="trackers-list">
      {trackers.map((t) => (
        <div key={t.id} className={`tracker-row ${t.is_default ? 'default' : ''}`}>
          <span className="tracker-icon">{t.icon}</span>
          <span className="tracker-name">{t.name}</span>
          {t.is_default && <span className="tracker-badge">базовый</span>}
        </div>
      ))}
      <button className="add-tracker-btn" onClick={onAdd}>+ Добавить трекер</button>
    </div>
  );
};
