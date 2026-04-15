# 📥 Импорт базы данных в ISPmanager

Пошаговая инструкция по импорту SQL файла через phpMyAdmin.

---

## 🎯 Быстрая инструкция (3 шага)

### 1. Откройте phpMyAdmin
1. Зайдите в **ISPmanager**
2. Перейдите в **Базы данных**
3. Найдите вашу базу (например: `u1893136_skilltracer.art-artel.s`)
4. Нажмите кнопку **"Web интерфейс БД"** (или иконку phpMyAdmin)

### 2. Импорт SQL файла
1. В phpMyAdmin **кликните на имя базы** слева (чтобы выбрать её)
2. Перейдите на вкладку **"Импорт"** (Import)
3. Нажмите **"Выберите файл"**
4. Выберите файл `database.sql` с вашего компьютера
5. Убедитесь что:
   - Кодировка: `utf8mb4`
   - Формат: `SQL`
6. Нажмите **"Вперед"** (Go)

### 3. Проверка
После импорта должно показать:
```
9 запросов выполнено успешно
```

В списке таблиц слева появятся:
- ✅ users
- ✅ custom_trackers  
- ✅ daily_entries
- ✅ entry_metrics
- ✅ week_reports
- ✅ groups
- ✅ group_members
- ✅ telegram_updates
- ✅ comments

---

## 🔍 Проверка на сайте

Откройте в браузере:
```
https://skilltracer.art-artel.su/verify_tables.php
```

Должно показать:
```
✅ ВСЕ ТАБЛИЦЫ СОЗДАНЫ!
```

Затем проверьте полную диагностику:
```
https://skilltracer.art-artel.su/test_db.php
```

В ответе должно быть:
```json
{
  "overall_status": "SUCCESS",
  "tests": {
    "connection": { "status": "OK" },
    "required_tables": { "status": "OK" }
  }
}
```

---

## ❌ Если импорт не работает

### Ошибка: "Access denied"
**Решение:** У вас нет прав на импорт. Обратитесь в поддержку хостинга или используйте SSH:
```bash
mysql -u u1893136_admin -p u1893136_skilltracer.art-artel.s < database.sql
```

### Ошибка: "Unknown database"
**Решение:** Сначала создайте базу в ISPmanager → Базы данных → Создать

### Ошибка: "Table already exists"
**Решение:** Это нормально, таблицы уже созданы. Проверьте через verify_tables.php

---

## 📋 После успешного импорта

1. ✅ verify_tables.php показывает "ВСЕ ТАБЛИЦЫ СОЗДАНЫ"
2. ✅ test_db.php показывает "overall_status": "SUCCESS"
3. ➡️ Установите webhook:
   ```
   https://skilltracer.art-artel.su/setup_webhook.php
   ```

---

**🎉 После импорта базы данных система готова к работе!**
