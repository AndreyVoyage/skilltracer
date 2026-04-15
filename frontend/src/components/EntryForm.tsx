import React, { useState } from 'react';
import type { Tracker } from '../hooks/useEntries';
import './EntryForm.css';

interface Props {
  trackers: Tracker[];
  initialValues: Record<number, number>;
  initialComment?: string;
  initialMood?: number | null;
  onSave: (values: Record<number, number>, comment: string, mood: number) => void;
  onCancel: () => void;
}

const moodEmojis = ['😭', '😟', '😐', '🙂', '😄'];

export const EntryForm: React.FC<Props> = ({ trackers, initialValues, initialComment = '', initialMood, onSave, onCancel }) => {
  const [values, setValues] = useState<Record<number, number>>(initialValues);
  const [comment, setComment] = useState(initialComment);
  const [mood, setMood] = useState<number>(initialMood ?? 3);

  return (
    <div className="entry-form">
      <div className="mood-row">
        {moodEmojis.map((emoji, i) => (
          <button
            key={i}
            className={mood === i + 1 ? 'active' : ''}
            onClick={() => setMood(i + 1)}
          >
            {emoji}
          </button>
        ))}
      </div>

      {trackers.map((t) => (
        <div key={t.id} className="tracker-input">
          <label>{t.icon} {t.name}</label>
          <div className="rating">
            {[1, 2, 3, 4, 5].map((v) => (
              <button
                key={v}
                className={values[t.id] === v ? 'active' : ''}
                onClick={() => setValues((prev) => ({ ...prev, [t.id]: v }))}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      ))}

      <label className="comment-label">Комментарий</label>
      <textarea
        rows={3}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Что произошло за день?"
      />

      <div className="form-actions">
        <button className="save-btn" onClick={() => onSave(values, comment, mood)}>
          Сохранить
        </button>
        <button className="cancel-btn" onClick={onCancel}>
          Отмена
        </button>
      </div>
    </div>
  );
};
