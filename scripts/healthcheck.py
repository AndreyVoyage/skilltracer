#!/usr/bin/env python3
"""
Skill Tracer - Health Check Script

Проверяет статус сервиса Skill Tracer:
- Доступность HTTP health endpoint
- Подключение к базе данных
- Статус systemd сервиса

Usage:
    python scripts/healthcheck.py
    # или:
    python scripts/healthcheck.py --url http://localhost:8000/health
"""

import argparse
import asyncio
import os
import subprocess
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv


def load_env() -> None:
    """Загружает .env из возможных путей."""
    candidates = [
        Path(".env"),
        Path(__file__).parent.parent / ".env",
        Path("/opt/skilltracer/.env"),
        Path("/opt/skilltracer/backend/.env"),
    ]
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            return


def check_systemd_service(service_name: str) -> dict:
    """Проверяет статус systemd сервиса."""
    result = {"status": "unknown", "active": False, "loaded": False, "details": ""}
    
    try:
        output = subprocess.check_output(
            ["systemctl", "is-active", service_name],
            stderr=subprocess.STDOUT,
            text=True,
        ).strip()
        result["active"] = output == "active"
        result["status"] = output
    except subprocess.CalledProcessError as e:
        result["status"] = e.output.strip() if e.output else "inactive"
    except FileNotFoundError:
        result["status"] = "systemctl_not_found"
        result["details"] = "systemctl недоступен (возможно не Linux)"
    
    try:
        subprocess.check_output(
            ["systemctl", "is-enabled", service_name],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        result["loaded"] = True
    except subprocess.CalledProcessError:
        result["loaded"] = False
    except FileNotFoundError:
        pass
    
    return result


async def check_http_health(url: str) -> dict:
    """Проверяет HTTP health endpoint."""
    result = {"ok": False, "status": 0, "data": None, "error": None}
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                result["status"] = resp.status
                try:
                    result["data"] = await resp.json()
                except Exception:
                    result["data"] = await resp.text()
                
                result["ok"] = resp.status == 200
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def check_database() -> dict:
    """Проверяет подключение к MySQL через DATABASE_URL."""
    result = {"ok": False, "error": None}
    
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        result["error"] = "DATABASE_URL не задан"
        return result
    
    try:
        # Асинхронная проверка через aiomysql
        import aiomysql
        
        # Парсим URL: mysql+aiomysql://user:pass@host:port/db
        url = database_url.replace("mysql+aiomysql://", "").replace("mysql+asyncmy://", "")
        creds, host_db = url.split("@", 1)
        user, password = creds.split(":", 1)
        host_port_db = host_db.split("/", 1)
        host_part = host_port_db[0]
        db = host_port_db[1] if len(host_port_db) > 1 else ""
        
        if ":" in host_part:
            host, port_str = host_part.rsplit(":", 1)
            port = int(port_str)
        else:
            host = host_part
            port = 3306
        
        conn = await aiomysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            db=db,
            connect_timeout=5,
        )
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            await cur.fetchone()
        conn.close()
        
        result["ok"] = True
    except ImportError:
        result["error"] = "aiomysql не установлен"
    except Exception as e:
        result["error"] = str(e)
    
    return result


async def main() -> int:
    parser = argparse.ArgumentParser(description="Skill Tracer Health Check")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/health",
        help="URL health endpoint",
    )
    parser.add_argument(
        "--service",
        default="skilltracer",
        help="Имя systemd сервиса",
    )
    args = parser.parse_args()
    
    load_env()
    
    print("=" * 50)
    print("Skill Tracer Health Check")
    print("=" * 50)
    
    # 1. Systemd
    print(f"\n🔍 Проверяем systemd сервис: {args.service}")
    svc = check_systemd_service(args.service)
    if svc["active"]:
        print(f"   ✅ Сервис активен ({svc['status']})")
    else:
        print(f"   ❌ Сервис НЕ активен ({svc['status']})")
    if svc["loaded"]:
        print("   ✅ Сервис загружен в systemd")
    else:
        print("   ⚠️  Сервис НЕ загружен в systemd")
    if svc["details"]:
        print(f"   ℹ️  {svc['details']}")
    
    # 2. HTTP Health
    print(f"\n🔍 Проверяем HTTP endpoint: {args.url}")
    http = await check_http_health(args.url)
    if http["ok"]:
        print(f"   ✅ HTTP 200 OK")
        if isinstance(http["data"], dict):
            for key, value in http["data"].items():
                print(f"      {key}: {value}")
    else:
        print(f"   ❌ HTTP недоступен (status={http['status']})")
        if http["error"]:
            print(f"      Ошибка: {http['error']}")
    
    # 3. Database
    print("\n🔍 Проверяем подключение к БД...")
    db = await check_database()
    if db["ok"]:
        print("   ✅ База данных доступна")
    else:
        print(f"   ❌ База данных недоступна")
        if db["error"]:
            print(f"      Ошибка: {db['error']}")
    
    # Summary
    all_ok = svc["active"] and http["ok"] and db["ok"]
    print("\n" + "=" * 50)
    if all_ok:
        print("🎉 Все проверки пройдены! Система работает.")
    else:
        print("⚠️  Есть проблемы. Проверьте вывод выше.")
    print("=" * 50)
    
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ Прервано")
        exit_code = 130
    sys.exit(exit_code)
