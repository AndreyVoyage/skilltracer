import { useState, useEffect, useCallback } from 'react';
import api from '../api/client';
import './MediaGallery.css';

export interface MediaItem {
  id?: string;
  type?: string;
  file_id?: string;
  caption?: string | null;
  created_at?: string;
}

interface Props {
  entryId: number;
  mediaItems: (MediaItem | string)[];
  onDelete?: () => void;
}

interface MediaState {
  url: string;
  loading: boolean;
  error: string;
}

function normalizeMedia(item: MediaItem | string): MediaItem | null {
  if (typeof item === 'string') {
    return { type: 'photo', file_id: item };
  }
  if (item && typeof item === 'object' && item.file_id) {
    return item;
  }
  return null;
}

function getItemKey(item: MediaItem, idx: number): string {
  return item.id || item.file_id || `idx-${idx}`;
}

export function MediaGallery({ entryId, mediaItems, onDelete }: Props) {
  const [mediaStates, setMediaStates] = useState<Record<string, MediaState>>({});

  const items = mediaItems.map(normalizeMedia).filter(Boolean) as MediaItem[];

  // Логирование для диагностики
  useEffect(() => {
    console.log('[MediaGallery] mediaItems received:', mediaItems);
    console.log('[MediaGallery] normalized count:', items.length);
    items.forEach((item, i) => {
      console.log(`[MediaGallery] [${i}] type=${item.type}, id=${item.id}, file_id=${item.file_id?.substring(0, 20)}...`);
    });
  }, [mediaItems]);

  // Загружаем свежие URLs для всех медиа
  useEffect(() => {
    const loadUrls = async () => {
      for (const item of items) {
        const key = getItemKey(item, 0);
        if (!item.file_id) continue;

        setMediaStates((prev) => ({
          ...prev,
          [key]: { url: '', loading: true, error: '' },
        }));

        try {
          const resp = await api.get(`/media/file-url/${item.file_id}`);
          setMediaStates((prev) => ({
            ...prev,
            [key]: { url: resp.data.url, loading: false, error: '' },
          }));
        } catch (e: any) {
          console.error(`Failed to load URL for ${item.file_id}:`, e);
          setMediaStates((prev) => ({
            ...prev,
            [key]: {
              url: '',
              loading: false,
              error: e.response?.data?.detail || 'Не удалось загрузить файл',
            },
          }));
        }
      }
    };

    if (items.length > 0) {
      loadUrls();
    }
  }, [mediaItems]);

  const handleDelete = useCallback(
    async (mediaId: string) => {
      if (!mediaId) return;
      if (!confirm('Удалить этот файл?')) return;

      try {
        await api.delete(`/media/entries/${entryId}/media/${mediaId}`);
        onDelete?.();
      } catch (e: any) {
        alert('Ошибка удаления: ' + (e.response?.data?.detail || e.message));
      }
    },
    [entryId, onDelete]
  );

  if (!items.length) return null;

  return (
    <div className="media-gallery">
      {items.map((item, idx) => {
        const key = getItemKey(item, idx);
        const state = mediaStates[key] || { url: '', loading: true, error: '' };
        const hasId = !!item.id;

        return (
          <div key={key} className="media-item">
            {/* Кнопка удаления (только если есть id) */}
            {hasId && (
              <button
                className="media-delete-btn"
                onClick={() => handleDelete(item.id!)}
                title="Удалить"
                aria-label="Удалить"
              >
                ✕
              </button>
            )}

            {/* Предупреждение для legacy формата */}
            {!hasId && (
              <div style={{
                position: 'absolute', top: '8px', left: '8px', zIndex: 10,
                background: '#f59e0b', color: '#000', padding: '4px 8px',
                borderRadius: '6px', fontSize: '11px', fontWeight: 'bold'
              }}>
                ⚠️ Legacy
              </div>
            )}

            {/* Состояние загрузки */}
            {state.loading && (
              <div className="media-loading">Загрузка...</div>
            )}

            {/* Ошибка */}
            {state.error && !state.loading && (
              <div className="media-error">❌ {state.error}</div>
            )}

            {/* Содержимое */}
            {!state.loading && !state.error && state.url && (
              <>
                {item.type === 'photo' && (
                  <img
                    src={state.url}
                    alt={item.caption || 'Фото'}
                    className="media-photo"
                    loading="lazy"
                    onError={() =>
                      setMediaStates((prev) => ({
                        ...prev,
                        [key]: { ...prev[key], error: 'Ошибка загрузки изображения' },
                      }))
                    }
                  />
                )}

                {(item.type === 'video' || item.type === 'video_note') && (
                  <video
                    src={state.url}
                    controls
                    className="media-video"
                    preload="metadata"
                    playsInline
                    onError={(e) => {
                      console.error('Video error:', e);
                      setMediaStates((prev) => ({
                        ...prev,
                        [key]: {
                          ...prev[key],
                          error:
                            'Видео не поддерживается (возможно кодек H.265). Запишите через Telegram.',
                        },
                      }));
                    }}
                  />
                )}

                {(item.type === 'voice' || item.type === 'audio') && (
                  <div className="media-audio-wrapper">
                    <span className="media-audio-icon">
                      {item.type === 'voice' ? '🎤' : '🎵'}
                    </span>
                    <audio
                      src={state.url}
                      controls
                      className="media-audio"
                      preload="metadata"
                      onError={() =>
                        setMediaStates((prev) => ({
                          ...prev,
                          [key]: { ...prev[key], error: 'Ошибка загрузки аудио' },
                        }))
                      }
                    />
                  </div>
                )}
              </>
            )}

            {/* Caption */}
            {item.caption && (
              <div className="media-caption">{item.caption}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
