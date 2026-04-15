#!/usr/bin/env python3
"""
Скрипт для создания единого файла контекста проекта ПРОЕКТ.MD
Собирает структуру директорий, код и конфигурации для передачи в Kimi
"""

import os
from datetime import datetime
from pathlib import Path

# Конфигурация исключений
EXCLUDED_DIRS = {
    'node_modules', '.git', '__pycache__', '.next', 'dist', 'build', 
    '.vscode', '.idea', 'coverage', '.nuxt', 'out', '.cache',
    'venv', 'env', '.env', '.venv', 'target', 'bin', 'obj',
    '.turbo', '.output', 'storybook-static', '__pycache__'
}

EXCLUDED_FILES = {
    '.DS_Store', 'Thumbs.db', '.gitignore', '.dockerignore',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
    'Cargo.lock', 'Gemfile.lock', '.eslintcache', '.prettierignore',
    'ПРОЕКТ.MD', 'create_context.py'
}

EXCLUDED_EXTENSIONS = {
    '.log', '.tmp', '.temp', '.swp', '.swo', '.bak', 
    '.min.js', '.min.css', '.map', '.lock'
}

# Бинарные форматы
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.mp3', '.mp4', '.wav', '.avi', '.mov',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.exe', '.dll', '.so', '.dylib', '.bin',
    '.ttf', '.woff', '.woff2', '.eot'
}

# Важные файлы для первоочередного включения
PRIORITY_FILES = [
    'package.json', 'tsconfig.json', 'requirements.txt', 'Dockerfile',
    'docker-compose.yml', 'README.md', '.env.example', 'next.config.js',
    'vite.config.ts', 'tailwind.config.js', 'nest-cli.json',
    'telegram-bot.py', 'bot.py', 'main.py', 'app.py'
]


def should_include(path, is_dir=False):
    """Проверяет, нужно ли включать файл/директорию"""
    name = path.name
    
    if is_dir:
        return name not in EXCLUDED_DIRS and not name.startswith('.')
    
    if name in EXCLUDED_FILES:
        return False
    
    if name.startswith('.') and name not in ['.env.example', '.env.local']:
        return False
    
    if any(str(path).endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return False
    
    return True


def get_file_priority(path):
    """Определяет приоритет файла для сортировки"""
    name = path.name
    if name in PRIORITY_FILES:
        return PRIORITY_FILES.index(name)
    return 999


def read_file_content(path):
    """Читает содержимое файла"""
    try:
        # Проверяем на бинарный формат
        if any(str(path).endswith(ext) for ext in BINARY_EXTENSIONS):
            return "[Бинарный файл - содержимое не отображается]"
        
        # Пытаемся прочитать как текст
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Ограничиваем размер (max 500KB на файл)
        max_size = 500 * 1024
        if len(content) > max_size:
            total = len(content)
            content = content[:max_size] + "\n\n[... Файл обрезан. Общий размер: " + str(total) + " символов]"
        
        return content
    except Exception as e:
        return "[Ошибка чтения файла: " + str(e) + "]"


def generate_tree(directory, prefix=""):
    """Генерирует дерево директорий в стиле Linux tree"""
    lines = []
    try:
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return prefix + "[Нет доступа]\n"
    
    visible_items = [item for item in items if should_include(item, item.is_dir())]
    
    result_lines = []
    for i, item in enumerate(visible_items):
        is_last = i == len(visible_items) - 1
        current_prefix = "└── " if is_last else "├── "
        
        result_lines.append(prefix + current_prefix + item.name)
        
        if item.is_dir():
            extension = "    " if is_last else "│   "
            subtree = generate_tree(item, prefix + extension)
            result_lines.append(subtree)
    
    return "\n".join(result_lines)


def collect_project_info(root_dir):
    """Собирает всю информацию о проекте"""
    files_data = []
    stats = {"total_files": 0, "total_size": 0, "languages": {}}
    
    # Собираем все файлы
    all_files = []
    for path in root_dir.rglob("*"):
        if path.is_file() and should_include(path.relative_to(root_dir)):
            all_files.append(path)
    
    # Сортируем: сначала приоритетные, затем по пути
    all_files.sort(key=lambda p: (get_file_priority(p), str(p)))
    
    for file_path in all_files:
        try:
            relative_path = file_path.relative_to(root_dir)
            content = read_file_content(file_path)
            size = file_path.stat().st_size
            
            # Статистика по языкам
            ext = file_path.suffix.lower()
            if ext:
                stats["languages"][ext] = stats["languages"].get(ext, 0) + 1
            
            stats["total_files"] += 1
            stats["total_size"] += size
            
            files_data.append({
                "path": str(relative_path),
                "size": size,
                "content": content
            })
        except Exception as e:
            print("Пропуск " + str(file_path) + ": " + str(e))
    
    return {"files": files_data, "stats": stats}


def create_project_md(root_dir, output_file="ПРОЕКТ.MD"):
    """Создает единый файл проекта"""
    print("Анализирую структуру проекта...")
    
    # Собираем информацию
    project_info = collect_project_info(root_dir)
    
    print("Найдено файлов: " + str(project_info['stats']['total_files']))
    print("Формирую ПРОЕКТ.MD...")
    
    # Формируем Markdown
    lines = []
    lines.append("# Контекст проекта Telegram Chatbot + Web App")
    lines.append("")
    lines.append("**Дата создания:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    lines.append("**Корневая директория:** `" + str(root_dir.absolute()) + "`")
    lines.append("")
    
    # Статистика
    lines.append("## Статистика проекта")
    lines.append("")
    stats = project_info["stats"]
    lines.append("- **Всего файлов:** " + str(stats['total_files']))
    lines.append("- **Общий размер:** " + str(round(stats['total_size'] / 1024, 1)) + " KB")
    lines.append("")
    lines.append("### Распределение по типам файлов:")
    for ext, count in sorted(stats["languages"].items(), key=lambda x: -x[1])[:10]:
        lines.append("- `" + ext + "`: " + str(count) + " файлов")
    lines.append("")
    
    # Структура директорий
    lines.append("## Структура проекта")
    lines.append("```")
    lines.append(root_dir.name + "/")
    lines.append(generate_tree(root_dir))
    lines.append("```")
    lines.append("")
    
    # Технологический стек
    lines.append("## Технологический стек (определен автоматически)")
    lines.append("")
    
    stack_hints = []
    file_names = [f["path"].lower() for f in project_info["files"]]
    
    if any("package.json" in f for f in file_names):
        stack_hints.append("- **Frontend:** React/Next.js (JavaScript/TypeScript)")
    if any("requirements.txt" in f for f in file_names):
        stack_hints.append("- **Backend:** Python (Flask/FastAPI/Django)")
    if any("telegram" in f or "bot.py" in f for f in file_names):
        stack_hints.append("- **Бот:** Telegram Bot API")
    if any("dockerfile" in f for f in file_names):
        stack_hints.append("- **Контейнеризация:** Docker")
    if any("prisma" in f or "schema.prisma" in f for f in file_names):
        stack_hints.append("- **ORM:** Prisma")
    if any("tailwind" in f for f in file_names):
        stack_hints.append("- **Стили:** Tailwind CSS")
    
    if stack_hints:
        lines.extend(stack_hints)
    else:
        lines.append("*Анализ зависимостей см. в файлах package.json/requirements.txt ниже*")
    lines.append("")
    
    # Содержимое файлов
    lines.append("## Содержимое файлов")
    lines.append("")
    lines.append("*Ниже приведены все исходные файлы проекта с их содержимым.*")
    lines.append("")
    
    for file_data in project_info["files"]:
        path = file_data["path"]
        content = file_data["content"]
        size = file_data["size"]
        
        # Определяем язык для подсветки синтаксиса
        ext = Path(path).suffix.lower()
        lang_map = {
            '.ts': 'typescript', '.tsx': 'tsx',
            '.js': 'javascript', '.jsx': 'jsx',
            '.py': 'python', '.json': 'json',
            '.md': 'markdown', '.yml': 'yaml', '.yaml': 'yaml',
            '.css': 'css', '.scss': 'scss', '.html': 'html',
            '.sh': 'bash', '.env': 'env', '.prisma': 'prisma',
            '.sql': 'sql', '.dockerfile': 'dockerfile'
        }
        lang = lang_map.get(ext, '')
        
        lines.append("### `" + path + "`")
        lines.append("*Размер: " + str(size) + " bytes*")
        lines.append("```" + lang)
        lines.append(content)
        lines.append("```")
        lines.append("")
    
    # Записываем файл
    output_path = root_dir / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    
    print("Готово! Файл сохранен: " + str(output_path))
    print("Размер файла: " + str(round(output_path.stat().st_size / 1024, 1)) + " KB")
    print("")
    print("Совет: Перед отправкой в Kimi проверьте размер файла.")
    print("   Если он слишком большой, исключите лишние медиа-файлы из проекта.")


if __name__ == "__main__":
    # Определяем корневую директорию (где запущен скрипт)
    root = Path.cwd()
    
    print("=" * 60)
    print("  Генератор контекста проекта для Kimi")
    print("=" * 60)
    print("")
    
    create_project_md(root)