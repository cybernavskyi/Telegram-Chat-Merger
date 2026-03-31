# 📱 Telegram → NotebookLM

![Version](https://img.shields.io/badge/version-3.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue)
![Python](https://img.shields.io/badge/python-3.11-yellow)

> Превращает экспорт чата Telegram в структурированный Markdown
> за один клик. Никаких браузеров, PDF и лишних шагов.

Разработано для **[HardCore Affiliate Club](https://t.me/hardcoreaffiliateclub)**.

---

## ⚡ Зачем это нужно

Telegram хранит историю чата в десятках HTML-файлов.
NotebookLM не умеет их читать напрямую.
Этот инструмент решает задачу полностью:
```
Папка с экспортом Telegram → один клик → Markdown файлы → NotebookLM
```

---

## 🚀 Быстрый старт

1. [Скачай EXE](https://github.com/cybernavskyi/Telegram-Chat-Merger/releases/latest)
2. Экспортируй чат в Telegram Desktop → `Настройки → Экспорт → Формат: HTML`
3. Перетащи папку с экспортом в окно программы
4. Нажми **ЭКСПОРТ В MARKDOWN**
5. Загрузи `.md` файлы в NotebookLM

---

## ✨ Возможности

### Умный экспорт
- **Структурированный Markdown** — каждое сообщение с автором и датой:
  `**Иван Петров** \`01.01.2026 12:34\``
- **Таймлайн по датам** — разделители `## 📅 01.01.2026`
  между днями для лучшей навигации в NotebookLM
- **Шапка с метаданными** — источник, период, список участников
  в начале каждого файла

### Качество контента
- **Фильтрация по дате** — экспортируй только нужный период,
  не весь чат за три года
- **Пропуск ботов** — автоматически убирает сообщения от ботов
  по паттернам никнеймов
- **Удаление мусора** — сервисные сообщения ("вступил в группу",
  "закреплено сообщение") не попадают в экспорт
- **Дедупликация** — убирает повторы на стыках файлов

### Производительность
- **Параллельный парсинг** — все HTML файлы обрабатываются
  одновременно через ThreadPoolExecutor
- **Авто-нарезка** — делит большие чаты на части по 5 MB,
  оптимальный размер для NotebookLM
- **Поддержка вложенных папок** — находит HTML файлы
  в подпапках экспорта

### UX
- **Предпросмотр** — количество сообщений, участников
  и диапазон дат до запуска экспорта
- **История папок** — быстрый доступ к 5 последним чатам
- **Drag & Drop** — просто перетащи папку в окно
- **Тёмная / светлая тема** — синхронизация с системой
- **Кэш анализа** — повторный выбор той же папки мгновенный

---

## 🛠️ Установка для разработчиков
```bash
# Создать окружение
conda create -n telegram-nlm python=3.11
conda activate telegram-nlm

# Установить зависимости
pip install -r requirements.txt

# Запустить
python main.py
```

---

## 📦 Сборка EXE
```bash
# Узнать путь к tkinterdnd2
python -c "import tkinterdnd2, os; print(os.path.dirname(tkinterdnd2.__file__))"

# Собрать (подставить путь из команды выше)
pyinstaller --noconfirm --onefile --windowed \
  --name "TelegramToNotebookLM_v3.0" \
  --add-data ";tkinterdnd2" \
  --hidden-import "customtkinter" \
  --clean --icon=NONE main.py
```

---

## 📋 Зависимости

| Библиотека | Версия | Назначение |
|---|---|---|
| customtkinter | 5.2.2 | UI |
| tkinterdnd2-universal | 1.7.3 | Drag & Drop |
| tkcalendar | 1.6.1 | Выбор дат |
| beautifulsoup4 | 4.12.3 | Парсинг HTML |
| lxml | 5.1.0 | Быстрый движок для BS4 |
| pyinstaller | 6.4.0 | Сборка EXE |

---

## © HardCore Affiliate Club, 2023–2026
[t.me/hardcoreaffiliateclub](https://t.me/hardcoreaffiliateclub)
