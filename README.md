# 📱 Telegram Merger & PDF Splitter v1.0

![Version](https://img.shields.io/badge/version-1.0-blue) ![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![Python](https://img.shields.io/badge/python-3.11-yellow)

Утилита для обработки экспортированных чатов Telegram. Позволяет объединять сотни HTML файлов с историей чата в один читаемый документ, готовить их к печати в PDF, а также нарезать большие PDF файлы для отправки в NotebookLM.

Разработано специально для **HardCore Affiliate Club**.

---

## 🚀 Возможности

### 1. HTML Merger (Объединение чатов)
* **Умная сортировка:** Правильно расставляет файлы `messages.html`, `messages2.html` и т.д. по порядку.
* **Очистка мусора:** Удаляет аватарки, сервисные сообщения ("joined group", "pinned message") и лишние отступы для экономии контекста нейросетей.
* **Встраивание медиа:** Опция конвертации картинок в Base64 (весь чат в одном файле).
* **PDF Ready:** Оптимизированный CSS для идеальной печати через браузер (Ctrl+P).

### 2. PDF Splitter (Нарезка)
* **Smart Split:** Разделяет огромные PDF файлы на части.
* **Лимит NotebookLM:** Автоматически подгоняет части под размер **<190 МБ**, необходимый для NotebookLM.
* **Защита от ошибок:** Не обрабатывает файлы, которые и так меньше лимита.

### 3. Интерфейс (UI)
* Современный дизайн (CustomTkinter).
* Поддержка Drag & Drop (перетаскивание файлов и папок).
* Темная и Светлая темы (синхронизация с системой).

---

## 🛠️ Установка и запуск (для разработчиков)

Проект использует **Anaconda / Miniconda**.

### 1. Подготовка окружения
Откройте **Anaconda Prompt** и выполните команды:

```bash
# Создание окружения
conda create -n telegram-merger-gui python=3.11
conda activate telegram-merger-gui

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Запуск исходного кода
```bash
python main.py
```

---

## 📦 Сборка в EXE (Build)

Для создания одиночного исполняемого файла (`.exe`) используется PyInstaller. 
Нам необходимо вручную указать путь к библиотеке `tkinterdnd2`, чтобы она корректно упаковалась в EXE.

**1. Найдите путь к библиотеке:**
Выполните эту команду в консоли, чтобы узнать, где лежит пакет:
```bash
python -c "import tkinterdnd2, os; print(os.path.dirname(tkinterdnd2.__file__))"
```
*Скопируйте полученный путь.*

**2. Запустите сборку:**
Замените `<ПУТЬ_ИЗ_ШАГА_1>` на ваш путь:

```bash
pyinstaller --noconfirm --onefile --windowed --name "TelegramMerger_v1.0" --add-data "<ПУТЬ_ИЗ_ШАГА_1>;tkinterdnd2" --hidden-import "pikepdf" --hidden-import "PIL" --hidden-import "customtkinter" --clean --icon=NONE main.py
```

---

## 📋 Зависимости (requirements.txt)

Мы используем минимальный набор библиотек для максимальной производительности:

* `customtkinter==5.2.2` — Современный UI.
* `tkinterdnd2-universal==1.7.3` — Drag & Drop для Windows.
* `pillow>=10.0.0` — Работа с изображениями.
* `beautifulsoup4==4.12.3` — Парсинг HTML.
* `lxml==5.1.0` — Быстрый движок для BS4.
* `pikepdf==8.13.0` — Быстрая обработка PDF (нарезка).
* `pyinstaller==6.4.0` — Сборщик EXE.

---

## 📝 Как пользоваться

### Шаг 1: Объединение (Merge)
1.  Экспортируйте чат из Telegram Desktop (формат HTML).
2.  Перетащите **папку** с чатом в окно программы.
3.  Нажмите **"СОЗДАТЬ MERGED HTML"**.
4.  После завершения нажмите **"🖨️ Печать в PDF"**.
5.  В браузере нажмите `Ctrl + P` и сохраните как PDF.

### Шаг 2: Нарезка (Split)
1.  Если итоговый PDF получился слишком большим, перейдите на вкладку **"2. PDF Splitter"**.
2.  Перетащите PDF файл.
3.  Нажмите **"РАЗДЕЛИТЬ"**.
4.  Получите файлы `_part1.pdf`, `_part2.pdf` в той же папке.

---

## © Авторские права

[HardCore Affiliate Club](https://t.me/hardcoreaffiliateclub)