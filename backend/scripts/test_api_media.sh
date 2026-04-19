#!/bin/bash
# Тест API - что он возвращает

USER_ID="6072711152"
TODAY=$(date +%Y-%m-%d)

# Определяем начало недели (понедельник)
DAY_OF_WEEK=$(date +%u)  # 1=Mon, 7=Sun
DIFF=$((DAY_OF_WEEK - 1))
MONDAY=$(date -d "${TODAY} - ${DIFF} days" +%Y-%m-%d)

echo "=== Тест API /entries/week (start=${MONDAY}) ==="
curl -s "https://skilltracer.art-artel.su/api/v1/entries/week?start_date=${MONDAY}&user_id=${USER_ID}" | python3 -m json.tool | grep -E 'entry_date|media_files|has_media|photo_file|video_file|voice_file' | head -30

echo ""
echo "=== Тест media/file-url (пример) ==="
# Примеры file_id для проверки (заменить на реальные при необходимости)
# curl -s "https://skilltracer.art-artel.su/api/v1/media/file-url/AgACAgIAAxk...?user_id=${USER_ID}" | python3 -m json.tool

echo ""
echo "=== Тест health ==="
curl -s "https://skilltracer.art-artel.su/health" | python3 -m json.tool
