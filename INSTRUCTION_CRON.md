# ⏰ Настройка Cron в ISPmanager

Инструкция по настройке автоматической обработки сообщений от Telegram.

---

## 🎯 Что делает Cron?

Cron запускает Python скрипт **каждую минуту**, который:
1. Проверяет очередь сообщений (таблица `telegram_updates`)
2. Обрабатывает непрочитанные сообщения (отвечает на команды)
3. Помечает обработанные как `processed = 1`

Без Cron бот не будет отвечать на сообщения!

---

## ⚙️ Настройка (3 шага)

### Шаг 1: Откройте планировщик
1. Зайдите в **ISPmanager**
2. Перейдите в раздел **Система** → **Планировщик CRON**
3. Нажмите кнопку **Создать**

### Шаг 2: Заполните форму

| Поле | Значение |
|------|----------|
| **Команда** | `cd /www/skilltracer.art-artel.su && /usr/bin/python3.9 backend/cron/process_updates.py >> logs/cron.log 2>&1` |
| **Описание** | Обработка сообщений Telegram бота |
| **Период** | Каждую минуту |

**Для поля "Период" выберите:** `* * * * *` (звездочки в каждом поле)

Или установите:
- Минута: `*`
- Час: `*`
- День: `*`
- Месяц: `*`
- День недели: `*`

### Шаг 3: Сохраните
Нажмите **Сохранить** (или **OK**)

---

## ✅ Проверка работы

### 1. Подождите 1-2 минуты
Cron запускается раз в минуту.

### 2. Проверьте логи
```bash
# По SSH
cat /www/skilltracer.art-artel.su/logs/cron.log
```

Или через Менеджер файлов ISPmanager откройте файл `logs/cron.log`

**Ожидаемый вывод:**
```
2024-01-15 10:30:00 - Starting processor...
2024-01-15 10:30:01 - Processed 0 updates
```

### 3. Тестовое сообщение
1. Отправьте боту `/start` в Telegram
2. Подождите 1 минуту
3. Проверьте:
   - Бот ответил?
   - Появилась запись в `logs/processor.log`?

---

## 🔍 Отладка

### Cron не запускается?

Проверьте путь к Python:
```bash
which python3.9
# Должно показать: /usr/bin/python3.9

# Если не найден, попробуйте:
which python3
```

Если `python3.9` не найден, замените в команде cron на `python3`.

### Ошибки в cron.log?

```bash
# Проверьте права
cd /www/skilltracer.art-artel.su
ls -la backend/cron/process_updates.py

# Должно быть: -rwxr-xr-x или -rw-r--r--
# Если нужно:
chmod 755 backend/cron/process_updates.py
```

### Ручной запуск для проверки

```bash
cd /www/skilltracer.art-artel.su
/usr/bin/python3.9 backend/cron/process_updates.py
```

Должно показать что-то вроде:
```
2024-01-15 10:30:00 - Starting processor...
2024-01-15 10:30:01 - Processed 0 updates
```

---

## 📋 Альтернативная команда (если python3.9 не работает)

Если `python3.9` не найден, используйте:

```bash
cd /www/skilltracer.art-artel.su && python3 backend/cron/process_updates.py >> logs/cron.log 2>&1
```

Или:

```bash
cd /www/skilltracer.art-artel.su && /usr/bin/python3 backend/cron/process_updates.py >> logs/cron.log 2>&1
```

---

## 🛑 Остановка Cron

Если нужно остановить обработку:

1. ISPmanager → Планировщик CRON
2. Найдите вашу задачу
3. Выберите и нажмите **Удалить**

Или измените команду, добавив `#` в начало:
```bash
# cd /www/skilltracer.art-artel.su && ... (закомментировано)
```

---

**После настройки Cron бот будет отвечать на сообщения с задержкой до 1 минуты.**
