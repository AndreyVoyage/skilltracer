import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Layout } from '../components/Layout';
import api from '../api/client';
import './PublicReport.css';

interface DayStat {
  entry_date: string;
  mood: number;
  metrics: { tracker_name: string; value: number }[];
}

interface ReportData {
  week_start: string;
  filled_days: number;
  avg_mood: number | null;
  days: DayStat[];
}

export const PublicReport: React.FC = () => {
  const { token } = useParams<{ token: string }>();
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .get(`/reports/public/${token}`)
      .then((res) => {
        setReport(res.data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [token]);

  if (loading) {
    return (
      <Layout>
        <div className="loading">Загрузка отчёта...</div>
      </Layout>
    );
  }

  if (error || !report) {
    return (
      <Layout>
        <div className="error">Отчёт не найден или ссылка недействительна</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <h2 className="report-title">📊 Публичный отчёт</h2>
      <div className="stats-row">
        <div className="stat-box">
          <div className="stat-number">{report.filled_days}</div>
          <div className="stat-label">Дней</div>
        </div>
        <div className="stat-box">
          <div className="stat-number">{report.avg_mood ?? '—'}</div>
          <div className="stat-label">Настроение</div>
        </div>
      </div>

      <div className="report-days">
        {report.days.map((day) => (
          <div key={day.entry_date} className="report-day">
            <div className="day-header">{day.entry_date}</div>
            <div className="day-mood">
              Настроение: {day.mood ? ['😭', '😟', '😐', '🙂', '😄'][day.mood - 1] : '—'}
            </div>
            <div className="day-metrics">
              {day.metrics.map((m, idx) => (
                <div key={idx} className="metric-line">
                  <span>{m.tracker_name}</span>
                  <span className="metric-value">{m.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Layout>
  );
};
