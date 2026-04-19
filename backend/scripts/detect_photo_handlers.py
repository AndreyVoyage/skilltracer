#!/usr/bin/env python3
"""
Детектор: кто обрабатывает фото в боте?
"""
import os

handlers_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app/bot/handlers")

print("🔍 ПОИСК ВСЕХ ОБРАБОТЧИКОВ ФОТО/ВИДЕО/ГОЛОСОВЫХ")
print("=" * 60)

for filename in sorted(os.listdir(handlers_dir)):
    if not filename.endswith('.py'):
        continue

    filepath = os.path.join(handlers_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Ищем обработчики медиа
    has_photo = 'F.photo' in content or 'photo_file_id' in content or "media_files.append" in content
    has_video = 'F.video' in content or 'video_file_id' in content
    has_voice = 'F.voice' in content or 'voice_file_id' in content

    if has_photo or has_video or has_voice:
        print(f"\n📁 {filename}:")
        if has_photo:
            print("   ✓ Обрабатывает ФОТО")
            # Ищем что именно делает с фото
            if 'photo_file_id =' in content:
                print("   ⚠️  ПИШЕТ В photo_file_id (СТАРАЯ СИСТЕМА, REPLACE)")
            if 'media_files.append' in content and ('photo' in content or '_make_media_item("photo"' in content):
                print("   ✓ ПИШЕТ В media_files (НОВАЯ СИСТЕМА, APPEND)")
        if has_video:
            print("   ✓ Обрабатывает ВИДЕО")
            if 'video_file_id =' in content:
                print("   ⚠️  ПИШЕТ В video_file_id (СТАРАЯ СИСТЕМА)")
        if has_voice:
            print("   ✓ Обрабатывает ГОЛОСОВЫЕ")
            if 'voice_file_id =' in content:
                print("   ⚠️  ПИШЕТ В voice_file_id (СТАРАЯ СИСТЕМА)")

print("\n" + "=" * 60)
print("💡 РЕКОМЕНДАЦИЯ:")
print("   Оставить ТОЛЬКО файл где есть media_files.append")
print("   Отключить/удалить файлы где есть photo_file_id =")
