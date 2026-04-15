import React from 'react';
import { useTheme } from '../hooks/useTheme';
import './ThemeToggle.css';

export const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="theme-toggle">
      <button
        className={`theme-btn ${theme === 'cozy' ? 'active' : ''}`}
        onClick={() => theme !== 'cozy' && toggleTheme()}
      >
        🏠
      </button>
      <button
        className={`theme-btn ${theme === 'neon' ? 'active' : ''}`}
        onClick={() => theme !== 'neon' && toggleTheme()}
      >
        💎
      </button>
    </div>
  );
};
