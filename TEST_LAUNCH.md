# 🚀 Запуск Skill Tracer в продакшен

Пошаговый чек-лист запуска бота на skilltracer.art-artel.su

---

## ✅ Предварительные проверки

Откройте: `https://skilltracer.art-artel.su/test_full.php`

Должно показать:
```json
{
  "overall_status": "READY_FOR_LAUNCH",
  "ready": true
}
```

Если `NEEDS_FIX` — исправьте ошибки перед продолжением.

---

## Шаг 1: Установка Webhook (1 минута)

### 1.1 Установите webhook
Откройте:
```
https://skilltracer.art-artel.su/setup_webhook.php
```

**Ожидаемый результат:**
```json
{
  "ok": true,
  "result": true,
  "description": "Webhook was set"
}
```

### 1.2 Проверьте статус
Откройте:
```
https://skilltracer.art-artel.su/check_webhook.php
```

**Ожидаемый результат:**
```json
{
  "status": "OK",
  "webhook_installed": true,
  "webhook_url": "https://skilltracer.art-artel.su/webhook.php"
}
```

✅ **Готово!** Webhook установлен.

---

## Шаг 2: Настройка Cron (2 минуты)

### 2.1 Создайте задачу в ISPmanager
1. ISPmanager → **Планировщик CRON**
2. **Создать**
3. Заполните:
   - **Команда**: `cd /www/skilltracer.art-artel.su && /usr/bin/python3.9 backend/cron/process_updates.py >> logs/cron.log 2>&1`
   - **Период**: Каждую минуту (`* * * * *`)
4. **Сохранить**

Подробнее в файле `INSTRUCTION_CRON.md`

### 2.2 Проверьте логи (через 2 минуты)
```bash
# По SSH
cat /www/skilltracer.art-artel.su/logs/cron.log
```

**Ожидаемый вывод:**
```
2024-01-15 10:30:00 - Starting processor...
2024-01-15 10:30:01 - Processed 0 updates
```

✅ **Готово!** Cron работает.

---

## Шаг 3: Тестирование бота (3 минуты)

### 3.1 Найдите бота в Telegram
- Откройте Telegram
- Найдите вашего бота по username (например: @SkillTracerBot)
- Или перейдите по ссылке: `t.me/YourBotUsername`

### 3.2 Отправьте /start
Отправьте боту команду `/start`

### 3.3 Дождитесь ответа
**Подождите 1 минуту** (пока сработает cron)

Бот должен ответить приветственным сообщением с кнопкой **"Открыть Skill Tracer"**

**Если бот ответил:** ✅ Тест пройден!

**Если бот не отвечает:** См. раздел "Отладка" ниже.

---

## Шаг 4: Проверка обработки

### 4.1 Проверьте webhook лог
```bash
cat /www/skilltracer.art-artel.su/logs/webhook.log
```

Должна быть запись о входящем сообщении от Telegram.

### 4.2 Проверьте cron лог
```bash
cat /www/skilltracer.art-artel.su/logs/cron.log
```

Должна быть запись об обработке сообщения.

### 4.3 Проверьте базу данных
```sql
-- В phpMyAdmin
SELECT * FROM telegram_updates ORDER BY id DESC LIMIT 5;
```

Последняя запись должна иметь:
- `processed = 1`
- `processed_at` заполнено временем

✅ **Готово!** Вся цепочка работает.

---

## Шаг 5: Тест Mini App (5 минут)

### 5.1 Откройте Mini App
1. В боте нажмите кнопку **"Открыть Skill Tracer"**
2. Должно открыться окно Mini App

### 5.2 Проверьте консоль браузера
Нажмите **F12** → вкладка **Console**

**Должно быть:**
- Нет красных ошибок (кроме возможных CORS в development)
- API запросы возвращают 200

### 5.3 Проверьте API вручную
```bash
curl https://skilltracer.art-artel.su/api/me.php
```

Должно вернуть:
```json
{"error":"Missing init data"}
```

Это нормально — значит API работает, просто требует авторизацию.

✅ **Готово!** Mini App работает.

---

## Шаг 6: Тест записи дня (опционально)

Если у вас уже есть готовый Mini App:

1. Создайте тестовую запись дня через интерфейс
2. Проверьте что появилась в таблице `daily_entries`:
```sql
SELECT * FROM daily_entries ORDER BY id DESC LIMIT 1;
```

✅ **Готово!** Все компоненты работают.

---

## 📋 Чек-лист готовности

- [ ] `test_full.php` показывает `READY_FOR_LAUNCH`
- [ ] Webhook установлен (`check_webhook.php` → `webhook_installed: true`)
- [ ] Cron настроен в ISPmanager
- [ ] Бот отвечает на `/start` через 1 минуту
- [ ] Сообщения сохраняются в `telegram_updates`
- [ ] Cron обрабатывает их (`processed = 1`)
- [ ] Mini App открывается без ошибок
- [ ] API доступен (200 OK)

---

## 🆘 Отладка (если что-то не работает)

### ❌ Бот не отвечает

**Проверьте:**
```bash
# 1. Webhook лог
cat logs/webhook.log
# Должны быть записи о входящих запросах

# 2. Cron лог
cat logs/cron.log
# Должны быть записи каждую минуту

# 3. Проверьте webhook статус
curl https://skilltracer.art-artel.su/check_webhook.php
# webhook_installed должен быть true
```

**Если webhook лог пуст:**
- Проверьте что домен доступен из интернета
- Проверьте SSL сертификат
- Переустановите webhook: `setup_webhook.php`

### ❌ Сообщения не обрабатываются

**Проверьте:**
```bash
# 1. Вручную запустите процессор
cd /www/skilltracer.art-artel.su
python3.9 backend/cron/process_updates.py

# 2. Проверьте ошибки
python3.9 backend/cron/process_updates.py 2>&1
```

**Если ошибка импорта:**
- Проверьте права на файлы: `chmod 755 backend/cron/`
- Проверьте Python: `python3.9 --version`

**Если ошибка БД:**
- Проверьте `backend/config/database.py`
- Убедитесь что все таблицы созданы

### ❌ Mini App не открывается

**Проверьте:**
1. SSL сертификат активен (Let's Encrypt)
2. Домен указан правильно в настройках бота (@BotFather → /setdomain)
3. Нет ошибок CORS в консоли браузера

### ❌ API возвращает 500

**Проверьте:**
```bash
# PHP логи (если доступны)
tail /var/log/php_errors.log

# Или включите отладку в api/me.php
error_reporting(E_ALL);
ini_set('display_errors', 1);
```

---

## 🎉 Поздравляем!

Если все пункты чек-листа отмечены — ваш **Skill Tracer** полностью работает!

### Что дальше?
- 🎨 Разрабатывайте React frontend для Mini App
- 👥 Добавляйте функционал групп и отчетов
- 📊 Создавайте аналитику и графики

### Полезные ссылки
- `test_full.php` — полный тест системы
- `health_check.php` — быстрая проверка здоровья
- `check_webhook.php` — статус webhook
- `verify_tables.php` — проверка таблиц БД

---

**Удачи с вашим Skill Tracer! 🚀**
