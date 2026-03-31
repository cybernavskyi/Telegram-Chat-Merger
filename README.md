# 📱 Telegram → NotebookLM v2.0

![Version](https://img.shields.io/badge/version-2.0-blue) ![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![Python](https://img.shields.io/badge/python-3.11-yellow)

Утилита для экспорта чатов Telegram в чистый TXT-формат,
оптимизированный для загрузки в NotebookLM.

Разработано специально для **HardCore Affiliate Club**.

---

## 🚀 Как это работает

1. Экспортируйте чат из Telegram Desktop (формат HTML)
2. Перетащите папку с экспортом в окно программы
3. Нажмите **"ЭКСПОРТ В TXT"**
4. Загрузите полученные TXT файлы в NotebookLM

Никаких браузеров. Никаких PDF. Один клик.

---

## ✨ Возможности

- **Умная сортировка** — правильный порядок файлов:
  `messages.html` → `messages2.html` → и т.д.
- **Метаданные** — каждое сообщение сохраняет автора и дату:
  `[Имя пользователя | 01.01.2026 12:34]`
- **Дедупликация** — убирает повторяющиеся сообщения
  на стыках файлов
- **Авто-нарезка** — делит большие чаты на части по 5 MB,
  оптимальный размер для NotebookLM
- **Очистка мусора** — удаляет сервисные сообщения
  ("вступил в группу", "закреплено сообщение")
- **Drag & Drop** — просто перетащи папку в окно
- **Тёмная/светлая тема** — синхронизация с системой

---

## 🛠️ Установка и запуск (для разработчиков)

Проект использует **Anaconda / Miniconda**.

### 1. Подготовка окружения
```bash
conda create -n telegram-nlm python=3.11
conda activate telegram-nlm
pip install -r requirements.txt
```

### 2. Запуск
```bash
python main.py
```

---

## 📦 Сборка в EXE

**1. Узнать путь к tkinterdnd2:**
```bash
python -c "import tkinterdnd2, os; print(os.path.dirname(tkinterdnd2.__file__))"
```

**2. Собрать EXE** (подставить путь из шага 1):
```bash
pyinstaller --noconfirm --onefile --windowed \
  --name "TelegramToNotebookLM_v2.0" \
  --add-data "<ПУТЬ_К_TKINTERDND2>;tkinterdnd2" \
  --hidden-import "customtkinter" \
  --clean --icon=NONE main.py
```

---

## 📋 Зависимости

- `customtkinter==5.2.2` — UI
- `tkinterdnd2-universal==1.7.3` — Drag & Drop
- `beautifulsoup4==4.12.3` — парсинг HTML
- `lxml==5.1.0` — быстрый движок для BS4
- `pyinstaller==6.4.0` — сборка EXE

---

## © HardCore Affiliate Club, 2023-2026
[t.me/hardcoreaffiliateclub](https://t.me/hardcoreaffiliateclub)
