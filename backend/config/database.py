"""
Database Configuration for Python

Shared Hosting - Reg.ru
Database: u1893136_skilltracer.art-artel.s
"""

import pymysql
from typing import Dict, Any, List, Optional

DB_CONFIG = {
    'host': 'localhost',
    'database': 'u1893136_skilltracer.art-artel.s',
    'user': 'u1893136_admin',
    'password': 'SkillTracer2024',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
}


def get_db_connection():
    """Get MySQL connection."""
    return pymysql.connect(**DB_CONFIG)


def fetch_one(query: str, params: tuple = ()) -> Optional[Dict]:
    """Fetch single row."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()) -> List[Dict]:
    """Fetch all rows."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        conn.close()


def execute(query: str, params: tuple = ()) -> int:
    """Execute query, return affected rows."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
