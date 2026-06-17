# SkillTracer

> **Life-tracking platform** — track habits, tasks, expenses, time, and skills via Telegram + web dashboard.

[![CI](https://github.com/AndreyVoyage/skilltracer/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreyVoyage/skilltracer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18%2B-blue)](https://react.dev/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/AndreyVoyage/skilltracer/blob/main/LICENSE)

**Live:** https://skilltracer.art-artel.su  
**Developed with:** [Voyage AI Framework](https://github.com/AndreyVoyage/Framework-voyage-mvp)

---

## 🚀 Features (Planned)

- 📱 **Telegram Bot** — Quick input via aiogram v3
- 🌐 **React Dashboard** — Visual analytics with Recharts
- 🔒 **Telegram OAuth** — Auth without passwords
- 📊 **Analytics** — Trends, heatmaps, goals, reports
- 🐳 **Docker** — Full stack in one `docker-compose up`
- 🤖 **AI-Driven** — Developed with Voyage Framework

---

## 📁 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI + SQLAlchemy 2.0 + PostgreSQL 16 |
| **Bot** | aiogram v3 + httpx |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind |
| **Infra** | Docker + Nginx + Let's Encrypt |
| **AI** | Voyage Framework (self-improving engine) |

---

## 🛠 Quick Start (Local)

```bash
# Clone
git clone https://github.com/AndreyVoyage/skilltracer.git
cd skilltracer

# Setup environment
cp .env.example .env
# Edit .env with your values

# Start everything
docker compose up -d

# Backend: http://localhost:8000/docs
# Frontend: http://localhost:3000
```

---

## 📖 Documentation

- **Architecture:** See `docs/architecture.md`
- **API Docs:** `http://localhost:8000/docs` (Swagger)
- **Voyage Framework:** https://andreyvoyage.github.io/Framework-voyage-mvp/

---

## 📝 License

MIT — AndreyVoyage
