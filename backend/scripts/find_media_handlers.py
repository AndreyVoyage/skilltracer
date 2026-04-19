#!/usr/bin/env python3
"""
Находит все места где обрабатываются фото/видео/голосовые
"""
import os
import re

files_to_check = [
    'app/bot/handlers/collection.py',
    'app/bot/handlers/photos.py',
    'app/bot/handlers/journal.py',
    'app/bot/__init__.py',
]

patterns = [
    (r'photo_file_id\s*=', 'REPLACE в photo_file_id'),
    (r'voice_file_id\s*=', 'REPLACE в voice_file_id'),
    (r'video_file_id\s*=', 'REPLACE в video_file_id'),
    (r'media_files\.append', 'APPEND в media_files (правильно)'),
    (r'\.photo\[', 'Обработка фото'),
    (r'\.video', 'Обработка видео'),
    (r'\.voice', 'Обработка голосовых'),
    (r'include_router\(photos', 'Подключен photos.py'),
    (r'@router\.message\(F\.photo\)', 'Handler фото'),
    (r'@router\.message\(F\.video\)', 'Handler видео'),
    (r'@router\.message\(F\.voice\)', 'Handler голосовых'),
]

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for filepath in files_to_check:
    full_path = os.path.join(base_dir, filepath)
    if not os.path.exists(full_path):
        print(f"❌ Файл не найден: {filepath}")
        continue

    print(f"\n{'='*60}")
    print(f"📁 {filepath}")
    print('='*60)

    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

        found_any = False
        for i, line in enumerate(lines, 1):
            for pattern, desc in patterns:
                if re.search(pattern, line):
                    found_any = True
                    start = max(0, i-3)
                    end = min(len(lines), i+2)
                    context = '\n'.join(f"    {j+1}: {lines[j]}" for j in range(start, end))
                    print(f"\n🔍 Найдено: {desc}")
                    print(f"   Строка {i}:")
                    print(context)

        if not found_any:
            print("  (нет совпадений)")
