import os
import sys
import glob
import webbrowser
import threading
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime
from pathlib import Path

# UI & Logic libraries
import customtkinter as ctk
from tkinter import filedialog, messagebox
from bs4 import BeautifulSoup, FeatureNotFound
try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False
# --- КОНФИГУРАЦИЯ ---
VERSION = "3.0.1"
ctk.set_default_color_theme("blue")
ctk.set_appearance_mode("System")

# --- FIX: DND PATH LOADER ---
def get_dnd_library_path():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'tkinterdnd2')
    import tkinterdnd2
    return os.path.dirname(tkinterdnd2.__file__)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    dnd_path = get_dnd_library_path()
    if os.path.exists(dnd_path):
        os.environ['TKDND_LIBRARY'] = dnd_path
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# Regex
RE_FILENAME_NUMS = re.compile(r'\d+')

# --- ЦВЕТОВАЯ ПАЛИТРА ---
C_TEXT_MAIN = ("#000000", "#FFFFFF")
C_TEXT_SEC = ("#1A1A1A", "#FFFFFF") # Адаптивный текст (Черный в Light, Белый в Dark)
C_DROP_BG = ("#FFFFFF", "#2B2B2B")

C_BTN_PRI_BG = ("#0060C0", "#1473E6") 
C_BTN_PRI_HOVER = ("#004E9C", "#0D62C9")

C_BTN_SEC_BG = ("#E0E0E0", "#3A3A3A")
C_BTN_SEC_HOVER = ("#D0D0D0", "#4A4A4A")

# --- ENGINE (TXT EXPORTER) ---
class TxtExporterEngine:
    """Экспорт чата Telegram в Markdown для NotebookLM"""

    @staticmethod
    def is_bot(author: str) -> bool:
        if not author:
            return False
        low = author.lower().strip()
        return (
            low.endswith('bot') or
            low.endswith('_bot') or
            '[bot]' in low or
            '(bot)' in low or
            low.startswith('bot_') or
            low == 'bot'
        )

    @staticmethod
    def _find_html_files(folder_path):
        """Находит все HTML файлы в папке и подпапках"""
        files = glob.glob(
            os.path.join(folder_path, "*.html")) + glob.glob(
            os.path.join(folder_path, "**", "*.html"),
            recursive=True)
        return list(set(files))

    @staticmethod
    def _detect_parser():
        """Определяет доступный HTML парсер"""
        try:
            BeautifulSoup("", 'lxml')
            return 'lxml'
        except FeatureNotFound:
            return 'html.parser'

    @staticmethod
    def _to_iso_date(date_str):
        """Конвертирует дату любого формата в YYYY-MM-DD"""
        if not date_str:
            return None
        chunk = date_str[:10]
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(chunk, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return None

    @staticmethod
    def custom_telegram_sort(file_path):
        filename = Path(file_path).name.lower()
        if filename == 'messages.html': return (0, '')
        numbers = RE_FILENAME_NUMS.findall(filename)
        if numbers: return (1, int(numbers[0]))
        return (2, filename)

    def export_stream(self, folder_path, output_path,
                      remove_service=True, max_size_mb=10,
                      date_from="", date_to="",
                      skip_bots=True):
        start_time = time.time()
        html_files = self._find_html_files(folder_path)
        if not html_files:
            raise FileNotFoundError("HTML файлы не найдены")

        sorted_files = sorted(html_files, key=self.custom_telegram_sort)
        total_files = len(sorted_files)

        parser = self._detect_parser()

        yield (0, f"🚀 MD Export | Engine: {parser}")

        seen_ids = set()
        total_messages = 0

        def make_header(part_n):
            lines = [
                "# 💬 Telegram Chat Export",
                "",
                f"| Параметр | Значение |",
                f"|----------|----------|",
                f"| Создан | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
                f"| Источник | {Path(folder_path).name} |",
                f"| Период | {date_from or 'начало'} — {date_to or 'конец'} |",
                f"| Часть | {part_n} |",
                f"| Участники | PLACEHOLDER |",
                "",
                "---",
                "",
            ]
            return "\n".join(lines) + "\n"

        try:
            chunk_num = 1
            limit_bytes = max_size_mb * 1024 * 1024
            created_files = [output_path]
            outfile = open(output_path, 'w', encoding='utf-8')
            outfile.write(make_header(chunk_num))

            current_date = None
            participants = set()

            try:
                # Параллельный парсинг файлов
                max_workers = min(4, os.cpu_count() or 1)
                parsed_results = {}

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(
                            self._parse_single_file,
                            fp, parser, remove_service,
                            date_from, date_to, skip_bots
                        ): fp for fp in sorted_files
                    }
                    completed = 0
                    for future in as_completed(futures):
                        completed += 1
                        file_path, messages = future.result()
                        parsed_results[file_path] = messages
                        yield (completed / total_files,
                               f"Парсинг [{completed}/{total_files}]: "
                               f"{Path(file_path).name}")

                # Записываем в правильном порядке
                for file_path in sorted_files:
                    messages = parsed_results.get(file_path, [])

                    for msg_data in messages:
                        if 'error' in msg_data:
                            outfile.write(
                                f"[ОШИБКА в {msg_data['filename']}: "
                                f"{msg_data['error']}]\n\n")
                            continue

                        msg_id = msg_data['id']
                        if msg_id and msg_id in seen_ids:
                            continue
                        if msg_id:
                            seen_ids.add(msg_id)

                        author = msg_data['author']
                        date_str = msg_data['date_str']
                        msg_date = msg_data['msg_date']
                        msg_date_iso = msg_data['msg_date_iso']
                        text = msg_data['text']

                        if author:
                            participants.add(author)

                        if msg_date_iso and msg_date_iso != current_date:
                            current_date = msg_date_iso
                            outfile.write(f"\n## 📅 {msg_date}\n\n")

                        if author:
                            header = f"**{author}** `{date_str}`"
                        else:
                            header = f"`{date_str}`"

                        # Сохраняем ссылки из текста в MD формате
                        line = f"{header}\n{text}"
                        outfile.write(line + "\n\n")
                        total_messages += 1

                        if outfile.tell() > limit_bytes:
                            chunk_num += 1
                            outfile.close()
                            base = output_path.replace('.md', '')
                            new_path = f"{base}_part{chunk_num}.md"
                            created_files.append(new_path)
                            outfile = open(new_path, 'w', encoding='utf-8')
                            outfile.write(make_header(chunk_num))
                            current_date = None

                elapsed = round(time.time() - start_time, 2)
                outfile.write(
                    f"\n---\n"
                    f"*Итого: {total_messages} сообщений за {elapsed} сек.*\n")
            finally:
                outfile.close()

            with open(created_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
            participants_str = ", ".join(sorted(participants)) if participants else "—"
            content = content.replace(
                "PLACEHOLDER",
                f"{participants_str} *(всего: {len(participants)})*"
            )
            with open(created_files[0], 'w', encoding='utf-8') as f:
                f.write(content)

            return True, (total_messages, elapsed, created_files)
        except Exception as e:
            return False, str(e)

    def _parse_single_file(self, file_path, parser,
                           remove_service, date_from, date_to,
                           skip_bots=True):
        """Парсит один HTML файл, возвращает список сообщений"""
        results = []
        try:
            with open(file_path, 'r',
                      encoding='utf-8', errors='ignore') as f:
                raw_html = f.read()

            soup = BeautifulSoup(raw_html, parser)
            messages = soup.find_all('div', class_='message')

            for msg in messages:
                msg_id = msg.get('id', '')

                if remove_service and 'service' in msg.get('class', []):
                    continue

                from_name_tag = msg.find(class_='from_name')
                author = from_name_tag.get_text(strip=True) \
                    if from_name_tag else ''

                if skip_bots and self.is_bot(author):
                    continue

                date_tag = msg.find(class_='date')
                date_str = ''
                if date_tag:
                    date_str = date_tag.get('title', '') or \
                               date_tag.get_text(strip=True)

                text_tag = msg.find(class_='text')
                text = ''
                if text_tag:
                    text = text_tag.get_text(separator=' ', strip=True)

                if not text.strip():
                    continue

                # Конвертируем дату в ISO
                msg_date = date_str[:10] if date_str else None
                msg_date_iso = self._to_iso_date(date_str)

                # Фильтр по дате
                if msg_date_iso:
                    if date_from and msg_date_iso < date_from:
                        continue
                    if date_to and msg_date_iso > date_to:
                        continue

                results.append({
                    'id': msg_id,
                    'author': author,
                    'date_str': date_str,
                    'msg_date': msg_date,
                    'msg_date_iso': msg_date_iso,
                    'text': text,
                })
        except Exception as e:
            results.append({'error': str(e),
                           'filename': Path(file_path).name})
        return file_path, results

    def analyze_folder(self, folder_path):
        html_files = self._find_html_files(folder_path)
        if not html_files:
            return None

        sorted_files = sorted(html_files, key=self.custom_telegram_sort)

        parser = self._detect_parser()

        total_messages = 0
        participants = set()
        dates = []
        is_valid_telegram = False

        for file_path in sorted_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_html = f.read()

                soup = BeautifulSoup(raw_html, parser)

                if soup.find(class_='message') or soup.find(class_='history'):
                    is_valid_telegram = True

                messages = soup.find_all('div', class_='message')
                for msg in messages:
                    if 'service' in msg.get('class', []):
                        continue
                    total_messages += 1

                    from_name_tag = msg.find(class_='from_name')
                    if from_name_tag:
                        name = from_name_tag.get_text(strip=True)
                        if not self.is_bot(name):
                            participants.add(name)

                    date_tag = msg.find(class_='date')
                    if date_tag:
                        date_str = date_tag.get('title', '')
                        if date_str and len(date_str) >= 10:
                            dates.append(date_str[:10])
            except:
                continue

        date_from = min(dates) if dates else '—'
        date_to = max(dates) if dates else '—'
        estimated_parts = max(1, total_messages // 5000)

        return {
            'is_valid': is_valid_telegram,
            'file_count': len(html_files),
            'total_messages': total_messages,
            'participants': sorted(participants),
            'date_from': date_from,
            'date_to': date_to,
            'estimated_parts': estimated_parts,
        }

# --- UI LAYER ---
BaseClass = ctk.CTk
if DND_AVAILABLE:
    class TkDnDWrapper(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    BaseClass = TkDnDWrapper

class TelegramMergerApp(BaseClass):
    def __init__(self):
        super().__init__()
        self.txt_exporter = TxtExporterEngine()
        self._analysis_cache = {}
        self._history = self._load_history()
        self._history_map = {}
        self.setup_window()
        self.create_ui()
        def _reset_progress():
            self.txt_progress.set(0)
            self.txt_progress.update_idletasks()
        self.after(200, _reset_progress)


    def setup_window(self):
        self.title(f"Telegram → NotebookLM v{VERSION}")
        self.geometry("700x650")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) 

    def create_ui(self):
        # HEADER
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))
        self.theme_opt = ctk.CTkOptionMenu(self.top_frame, values=["System", "Dark", "Light"],
            command=self.change_theme, width=100, fg_color=C_BTN_SEC_BG, text_color=C_TEXT_SEC)
        self.theme_opt.pack(side="right")
        self.theme_opt.set("System")
        ctk.CTkLabel(self.top_frame, text="Theme:", font=("Segoe UI", 12), text_color=C_TEXT_MAIN).pack(side="right", padx=10)

        # TABS
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.tab_txt = self.tabview.add("Экспорт для NotebookLM")
        self.setup_txt_tab()

        # FOOTER
        self.footer_lbl = ctk.CTkLabel(
            self, 
            text="© HardCore Affiliate Club, 2023-2026",
            font=("Segoe UI", 12, "underline"),
            text_color=C_BTN_PRI_BG[1], 
            cursor="hand2"
        )
        self.footer_lbl.grid(row=2, column=0, pady=(0, 10))
        self.footer_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/hardcoreaffiliateclub"))

    def change_theme(self, new_theme: str): ctk.set_appearance_mode(new_theme)

    # --- HANDLERS ---
    def clean_path(self, data): return data.strip().strip('{}').strip('"')

    def setup_txt_tab(self):
        t = self.tab_txt
        t.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(t, text="Экспорт чата в Markdown для NotebookLM",
            font=("Segoe UI", 20, "bold"), text_color=C_TEXT_MAIN).pack(pady=(8, 3))

        self.txt_drop = ctk.CTkLabel(t,
            text="📁 Перетащи папку чата сюда\nИЛИ нажми для выбора",
            fg_color=C_DROP_BG, text_color=C_TEXT_MAIN, height=90, corner_radius=8)
        self.txt_drop.pack(fill="x", padx=20, pady=3)

        if DND_AVAILABLE:
            self.txt_drop.drop_target_register(DND_FILES)
            self.txt_drop.dnd_bind('<<Drop>>', self.on_drop_txt)
        self.txt_drop.bind("<Button-1>", lambda _: self.select_folder_txt())

        ctk.CTkButton(t, text="Выбрать папку",
            command=self.select_folder_txt, width=150,
            fg_color=C_BTN_SEC_BG, hover_color=C_BTN_SEC_HOVER,
            text_color=C_TEXT_SEC).pack(anchor="w", padx=20, pady=3)

        self.history_opt = ctk.CTkOptionMenu(t,
            values=["📋 Последние папки..."],
            command=self._select_from_history,
            width=200,
            fg_color=C_BTN_SEC_BG,
            text_color=C_TEXT_SEC)
        self.history_opt.pack(anchor="w", padx=20, pady=(0, 5))
        self._refresh_history_menu()

        opt_frame1 = ctk.CTkFrame(t, fg_color="transparent")
        opt_frame1.pack(fill="x", padx=20, pady=(5, 2))

        self.txt_clean_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame1,
            text="Удалить сервисные сообщения",
            variable=self.txt_clean_var,
            text_color=C_TEXT_MAIN).pack(side="left")

        self.txt_split_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame1,
            text="Авто-нарезка по 5 MB (для NotebookLM)",
            variable=self.txt_split_var,
            text_color=C_TEXT_MAIN).pack(side="left", padx=(20, 0))

        opt_frame2 = ctk.CTkFrame(t, fg_color="transparent")
        opt_frame2.pack(fill="x", padx=20, pady=(2, 5))

        self.skip_bots_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame2,
            text="Пропускать сообщения от ботов",
            variable=self.skip_bots_var,
            text_color=C_TEXT_MAIN).pack(side="left")

        self.date_frame = ctk.CTkFrame(t, fg_color="transparent")
        self.date_frame.pack(fill="x", padx=20, pady=(0, 8))

        ctk.CTkLabel(self.date_frame, text="Период:",
            font=("Segoe UI", 12), text_color=C_TEXT_MAIN).pack(
            side="left", padx=(0, 8))

        self.date_from_var = ctk.StringVar(value="")
        self.date_to_var = ctk.StringVar(value="")

        if CALENDAR_AVAILABLE:
            self.date_from_entry = DateEntry(self.date_frame,
                width=12, date_pattern='yyyy-mm-dd')
            self.date_from_entry.pack(side="left", padx=(0, 5))
            self.date_from_entry.delete(0, "end")

            ctk.CTkLabel(self.date_frame, text="—",
                text_color=C_TEXT_MAIN).pack(side="left", padx=5)

            self.date_to_entry = DateEntry(self.date_frame,
                width=12, date_pattern='yyyy-mm-dd')
            self.date_to_entry.pack(side="left", padx=(5, 0))
            self.date_to_entry.delete(0, "end")
        else:

            self.date_from_entry = ctk.CTkEntry(self.date_frame,
                textvariable=self.date_from_var,
                placeholder_text="с ГГГГ-ММ-ДД",
                width=130)
            self.date_from_entry.pack(side="left", padx=(0, 5))

            ctk.CTkLabel(self.date_frame, text="—",
                text_color=C_TEXT_MAIN).pack(side="left", padx=5)

            self.date_to_entry = ctk.CTkEntry(self.date_frame,
                textvariable=self.date_to_var,
                placeholder_text="по ГГГГ-ММ-ДД",
                width=130)
            self.date_to_entry.pack(side="left", padx=(5, 0))

        self.date_reset_btn = ctk.CTkButton(self.date_frame,
            text="✕",
            command=self._reset_date_filter,
            width=28, height=28,
            fg_color=C_BTN_SEC_BG,
            hover_color=C_BTN_SEC_HOVER,
            text_color=C_TEXT_SEC)
        self.date_reset_btn.pack(side="left", padx=(8, 0))

        self.txt_btn = ctk.CTkButton(t, text="ЭКСПОРТ В MARKDOWN",
            state="disabled", command=self.start_txt_export, height=45,
            font=("Segoe UI", 14, "bold"),
            fg_color=C_BTN_PRI_BG, hover_color=C_BTN_PRI_HOVER,
            text_color="#FFFFFF")
        self.txt_btn.pack(fill="x", padx=20, pady=(8, 3))

        self.txt_open_btn = ctk.CTkButton(t,
            text="📂 Открыть папку с результатом",
            state="disabled",
            command=self._open_result_folder,
            height=35,
            fg_color=C_BTN_SEC_BG,
            hover_color=C_BTN_SEC_HOVER,
            text_color=C_TEXT_SEC)
        self.txt_open_btn.pack(fill="x", padx=20, pady=(0, 3))

        self.txt_log = ctk.CTkTextbox(t, height=100,
            text_color=C_TEXT_MAIN, fg_color=C_DROP_BG)
        self.txt_log.pack(fill="x", padx=20, pady=5)

        self.txt_progress = ctk.CTkProgressBar(t,
            progress_color=C_BTN_PRI_BG[0],
            mode="determinate")
        self.txt_progress.pack(fill="x", padx=20, pady=(0, 5))
        self.txt_progress.set(0)

    def on_drop_txt(self, event):
        p = self.clean_path(event.data)
        if os.path.isdir(p):
            self.load_txt_folder(p)

    def select_folder_txt(self):
        p = filedialog.askdirectory()
        if p:
            self.load_txt_folder(p)

    def load_txt_folder(self, path):
        self.txt_progress.set(0)
        self.txt_open_btn.configure(state="disabled")
        self._save_to_history(path)
        self.txt_folder = path
        count = len(self.txt_exporter._find_html_files(path))
        self.txt_drop.configure(
            text=f"📂 Папка: {Path(path).name}\nНайдено HTML файлов: {count}")
        self.txt_log.insert("end", f"📂 Загружена папка: {path}\n")
        self.txt_btn.configure(state="disabled")
        self.txt_log.insert("end", "🔍 Анализ папки...\n")
        threading.Thread(
            target=self._run_analysis,
            args=(path, count),
            daemon=True).start()

    def _run_analysis(self, path, file_count):
        if file_count == 0:
            self.after(0, lambda: self.txt_log.insert(
                "end", "⚠️ В папке нет HTML файлов!\n"))
            return

        mtime = os.path.getmtime(path)
        cache_key = f"{path}_{mtime}"

        if cache_key in self._analysis_cache:
            self.after(0, lambda: self.txt_log.insert(
                "end", "⚡ Результат из кэша\n"))
            info = self._analysis_cache[cache_key]
        else:
            info = self.txt_exporter.analyze_folder(path)
            if info:
                self._analysis_cache[cache_key] = info

        self.after(0, lambda: self._show_analysis(info))

    def _show_analysis(self, info):
        if not info:
            self.txt_log.insert("end", "⚠️ Не удалось проанализировать папку\n")
            return

        if not info['is_valid']:
            self.txt_log.insert(
                "end",
                "⚠️ Папка не похожа на экспорт Telegram.\n"
                "Убедись что экспорт сделан в формате HTML.\n"
            )
            self.txt_btn.configure(state="disabled")
            return

        summary = (
            f"✅ Экспорт Telegram определён\n"
            f"📄 HTML файлов: {info['file_count']}\n"
            f"💬 Сообщений: {info['total_messages']}\n"
            f"👥 Участников: {len(info['participants'])}\n"
            f"📅 Период: {info['date_from']} — {info['date_to']}\n"
            f"📦 Файлов на выходе: ~{info['estimated_parts']}\n"
        )
        self.txt_log.insert("end", summary)
        self.txt_log.see("end")
        self.txt_btn.configure(state="normal")

        if info['date_from'] != '—':
            iso = self.txt_exporter._to_iso_date(info['date_from'])
            d = datetime.strptime(iso, "%Y-%m-%d").date() if iso else None
            self.date_from_var.set(
                self.txt_exporter._to_iso_date(info['date_from']) or "")
            if d and CALENDAR_AVAILABLE:
                try:
                    self.date_from_entry.set_date(d)
                except: pass

        if info['date_to'] != '—':
            iso = self.txt_exporter._to_iso_date(info['date_to'])
            d = datetime.strptime(iso, "%Y-%m-%d").date() if iso else None
            self.date_to_var.set(
                self.txt_exporter._to_iso_date(info['date_to']) or "")
            if d and CALENDAR_AVAILABLE:
                try:
                    self.date_to_entry.set_date(d)
                except: pass

    def _get_date_str(self, entry):
        """Извлекает дату в формате YYYY-MM-DD из любого entry"""
        raw = entry.get().strip()
        if not raw:
            return ""
        # Пробуем разные форматы которые может вернуть DateEntry
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%y",
                    "%Y-%m-%d %H:%M:%S", "%d.%m.%Y %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # Берём первые 10 символов как запасной вариант
        return raw[:10] if len(raw) >= 10 else ""

    def _reset_date_filter(self):
        if CALENDAR_AVAILABLE:
            self.date_from_entry.delete(0, "end")
            self.date_to_entry.delete(0, "end")
        else:
            self.date_from_var.set("")
            self.date_to_var.set("")

    def start_txt_export(self):
        if not hasattr(self, 'txt_folder'):
            return
        self.txt_btn.configure(state="disabled")
        self.txt_open_btn.configure(state="disabled")
        threading.Thread(
            target=self.run_txt_export,
            args=(
                self.txt_clean_var.get(),
                self.txt_split_var.get(),
                self._get_date_str(self.date_from_entry),
                self._get_date_str(self.date_to_entry),
                self.skip_bots_var.get(),
            ),
            daemon=True).start()

    def run_txt_export(self, do_clean, do_split, date_from, date_to, skip_bots):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.txt_output = os.path.join(
            self.txt_folder, f"Chat_Export_{ts}.md")
        try:
            gen = self.txt_exporter.export_stream(
                self.txt_folder, self.txt_output,
                remove_service=do_clean,
                max_size_mb=5 if do_split else 99999,
                date_from=date_from,
                date_to=date_to,
                skip_bots=skip_bots)
            while True:
                item = next(gen)
                self.after(0, lambda v=item: self.txt_progress.set(v[0]))
                self.after(0, lambda v=item: self.txt_log.insert("end", v[1] + "\n"))
        except StopIteration as e:
            self.after(0, lambda r=e.value: self.finish_txt_export(r))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def finish_txt_export(self, result):
        self.txt_btn.configure(state="normal")
        success, data = result
        if success:
            self.txt_progress.set(1.0)
            msgs, tm, files = data
            parts_info = f"{len(files)} часть(ей)" if len(files) > 1 else "1 файл"
            msg = f"✅ Готово! {msgs} сообщений, {parts_info}, за {tm} сек.\n"
            for f in files:
                msg += f"  📄 {Path(f).name}\n"
            self.txt_log.insert("end", msg)
            self.txt_log.see("end")
            files_list = "\n".join(Path(f).name for f in files)
            messagebox.showinfo("Готово",
                f"Экспорт завершён!\n\n"
                f"Сообщений: {msgs}\n"
                f"Файлов: {len(files)}\n\n"
                f"{files_list}")
            self.txt_open_btn.configure(state="normal")
        else:
            self.txt_log.insert("end", f"❌ Ошибка: {data}\n")

    def _open_result_folder(self):
        if hasattr(self, 'txt_output'):
            folder = os.path.dirname(self.txt_output)
            try:
                os.startfile(folder)
            except:
                try:
                    import subprocess
                    subprocess.Popen(['explorer', folder])
                except:
                    messagebox.showinfo(
                        "Папка", f"Результат сохранён в:\n{folder}")

    def _load_history(self):
        """Загружает историю папок из файла"""
        history_path = os.path.join(
            os.path.expanduser("~"), ".telegram_nlm_history")
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                paths = [line.strip() for line in f.readlines()]
                return [p for p in paths if os.path.isdir(p)]
        except:
            return []

    def _save_to_history(self, path):
        """Сохраняет папку в историю (максимум 5)"""
        if path in self._history:
            self._history.remove(path)
        self._history.insert(0, path)
        self._history = self._history[:5]
        history_path = os.path.join(
            os.path.expanduser("~"), ".telegram_nlm_history")
        try:
            with open(history_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(self._history))
        except:
            pass
        self._refresh_history_menu()

    def _refresh_history_menu(self):
        if self._history:
            short = [Path(p).name for p in self._history]
            self.history_opt.configure(values=short)
            self.history_opt.set("📋 Последние папки...")
            self._history_map = dict(zip(short, self._history))
        else:
            self.history_opt.configure(
                values=["📋 Последние папки..."])

    def _select_from_history(self, selected_name):
        if selected_name in self._history_map:
            self.load_txt_folder(self._history_map[selected_name])

if __name__ == "__main__":
    app = TelegramMergerApp()
    app.mainloop()