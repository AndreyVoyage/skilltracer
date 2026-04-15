import React from 'react';
import { ThemeToggle } from './ThemeToggle';
import './Layout.css';

interface Props {
  children: React.ReactNode;
}

export const Layout: React.FC<Props> = ({ children }) => {
  return (
    <div className="layout">
      <header className="app-header">
        <h1>📊 Skill Tracer</h1>
        <ThemeToggle />
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
};
