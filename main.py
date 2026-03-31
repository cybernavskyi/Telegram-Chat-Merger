import os
import sys
import glob
import webbrowser
import threading
import re
import time
from datetime import datetime
from pathlib import Path

# UI & Logic libraries
import customtkinter as ctk
from tkinter import filedialog, messagebox
from bs4 import BeautifulSoup, FeatureNotFound
# --- КОНФИГУРАЦИЯ ---
VERSION = "2.0.1"
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
C_TEXT_BTN = "#FFFFFF"          # Белый текст (для главных цветных кнопок)
C_TEXT_SEC = ("#1A1A1A", "#FFFFFF") # Адаптивный текст (Черный в Light, Белый в Dark)
C_DROP_BG = ("#FFFFFF", "#2B2B2B")

C_BTN_PRI_BG = ("#0060C0", "#1473E6") 
C_BTN_PRI_HOVER = ("#004E9C", "#0D62C9")

C_BTN_SEC_BG = ("#E0E0E0", "#3A3A3A")
C_BTN_SEC_HOVER = ("#D0D0D0", "#4A4A4A")

# --- ENGINE (TXT EXPORTER) ---
class TxtExporterEngine:
    """Engine 3: Экспорт в чистый TXT для NotebookLM"""

    @staticmethod
    def custom_telegram_sort(file_path):
        filename = Path(file_path).name.lower()
        if filename == 'messages.html': return (0, '')
        numbers = RE_FILENAME_NUMS.findall(filename)
        if numbers: return (1, int(numbers[0]))
        return (2, filename)

    def export_stream(self, folder_path, output_path, remove_service=True, max_size_mb=10):
        start_time = time.time()
        html_files = glob.glob(os.path.join(folder_path, "*.html"))
        if not html_files:
            raise FileNotFoundError("HTML файлы не найдены")

        sorted_files = sorted(html_files, key=self.custom_telegram_sort)
        total_files = len(sorted_files)

        parser = 'lxml'
        try: BeautifulSoup("", 'lxml')
        except FeatureNotFound: parser = 'html.parser'

        yield (0, f"🚀 TXT Export | Engine: {parser}")

        seen_ids = set()
        total_messages = 0

        def make_header(part_n):
            lines = [
                "=== TELEGRAM CHAT EXPORT ===",
                f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Источник: {Path(folder_path).name}",
                f"Часть: {part_n}",
                "=" * 40,
                ""
            ]
            return "\n".join(lines) + "\n"

        try:
            chunk_num = 1
            limit_bytes = max_size_mb * 1024 * 1024
            created_files = [output_path]
            outfile = open(output_path, 'w', encoding='utf-8')
            outfile.write(make_header(chunk_num))

            try:
                for i, file_path in enumerate(sorted_files, 1):
                    filename = Path(file_path).name
                    yield (i / total_files, f"Обработка [{i}/{total_files}]: {filename}")

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            raw_html = f.read()

                        soup = BeautifulSoup(raw_html, parser)
                        messages = soup.find_all('div', class_='message')

                        for msg in messages:
                            msg_id = msg.get('id', '')
                            if msg_id and msg_id in seen_ids:
                                continue
                            if msg_id:
                                seen_ids.add(msg_id)

                            if remove_service and 'service' in msg.get('class', []):
                                continue

                            from_name_tag = msg.find(class_='from_name')
                            author = from_name_tag.get_text(strip=True) if from_name_tag else ''

                            date_tag = msg.find(class_='date')
                            date_str = ''
                            if date_tag:
                                date_str = date_tag.get('title', '') or date_tag.get_text(strip=True)

                            text_tag = msg.find(class_='text')
                            text = ''
                            if text_tag:
                                text = text_tag.get_text(separator=' ', strip=True)

                            media_parts = []
                            for img in msg.find_all('img'):
                                src = img.get('src', '')
                                if src and not src.startswith('data:'):
                                    media_parts.append(f"[Фото: {Path(src).name}]")
                            for a in msg.find_all('a', href=True):
                                href = a['href']
                                if any(href.endswith(ext) for ext in
                                       ['.mp4', '.mov', '.avi', '.mp3', '.ogg', '.wav',
                                        '.pdf', '.doc', '.docx', '.zip']):
                                    media_parts.append(f"[Файл: {Path(href).name}]")

                            full_text = text + (' '.join(media_parts) if media_parts else '')
                            if not full_text.strip():
                                continue

                            header = f"[{author} | {date_str}]" if author else f"[{date_str}]"
                            line = f"{header}\n{text}"
                            if media_parts:
                                line += '\n' + ' '.join(media_parts)
                            outfile.write(line + "\n\n")
                            total_messages += 1

                            if outfile.tell() > limit_bytes:
                                chunk_num += 1
                                outfile.close()
                                base = output_path.replace('.txt', '')
                                new_path = f"{base}_part{chunk_num}.txt"
                                created_files.append(new_path)
                                outfile = open(new_path, 'w', encoding='utf-8')
                                outfile.write(make_header(chunk_num))

                    except Exception as e:
                        outfile.write(f"[ОШИБКА в {filename}: {e}]\n\n")

                elapsed = round(time.time() - start_time, 2)
                outfile.write(f"\n=== ИТОГО: {total_messages} сообщений | {elapsed} сек ===\n")
            finally:
                outfile.close()

            return True, (total_messages, elapsed, created_files)
        except Exception as e:
            return False, str(e)

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
        self.setup_window()
        self.create_ui()

    def setup_window(self):
        self.title(f"Telegram → NotebookLM v{VERSION}")
        self.geometry("700x500")
        self.resizable(False, False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) 

    def create_ui(self):
        # HEADER
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(10, 0))
        
        # Исправлен цвет текста в переключателе тем (тоже используется вторичный стиль)
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

        ctk.CTkLabel(t, text="Экспорт чата в TXT для NotebookLM",
            font=("Segoe UI", 20, "bold"), text_color=C_TEXT_MAIN).pack(pady=(10, 5))

        self.txt_drop = ctk.CTkLabel(t,
            text="📁 Перетащи папку чата сюда\nИЛИ нажми для выбора",
            fg_color=C_DROP_BG, text_color=C_TEXT_MAIN, height=90, corner_radius=8)
        self.txt_drop.pack(fill="x", padx=20, pady=5)

        if DND_AVAILABLE:
            self.txt_drop.drop_target_register(DND_FILES)
            self.txt_drop.dnd_bind('<<Drop>>', self.on_drop_txt)
        self.txt_drop.bind("<Button-1>", lambda _: self.select_folder_txt())

        ctk.CTkButton(t, text="Выбрать папку",
            command=self.select_folder_txt, width=150,
            fg_color=C_BTN_SEC_BG, hover_color=C_BTN_SEC_HOVER,
            text_color=C_TEXT_SEC).pack(pady=5)

        opt_frame = ctk.CTkFrame(t, fg_color="transparent")
        opt_frame.pack(fill="x", padx=20, pady=0)
        self.txt_clean_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame, text="Удалить сервисные сообщения",
            variable=self.txt_clean_var, text_color=C_TEXT_MAIN).pack(side="left")
        self.txt_split_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame,
            text="Авто-нарезка по 5 MB (для NotebookLM)",
            variable=self.txt_split_var,
            text_color=C_TEXT_MAIN).pack(side="left", padx=(20, 0))

        self.txt_btn = ctk.CTkButton(t, text="ЭКСПОРТ В TXT",
            state="disabled", command=self.start_txt_export, height=45,
            font=("Segoe UI", 14, "bold"),
            fg_color=C_BTN_PRI_BG, hover_color=C_BTN_PRI_HOVER,
            text_color=C_TEXT_BTN)
        self.txt_btn.pack(fill="x", padx=20, pady=(10, 5))

        self.txt_log = ctk.CTkTextbox(t, height=120,
            text_color=C_TEXT_MAIN, fg_color=C_DROP_BG)
        self.txt_log.pack(fill="x", padx=20, pady=10)

        self.txt_progress = ctk.CTkProgressBar(t, progress_color=C_BTN_PRI_BG[0])
        self.txt_progress.pack(fill="x", padx=20, pady=(0, 10))
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
        self.txt_folder = path
        count = len(glob.glob(os.path.join(path, "*.html")))
        self.txt_drop.configure(
            text=f"📂 Папка: {Path(path).name}\nНайдено HTML файлов: {count}")
        self.txt_log.insert("end", f"📂 Загружена папка: {path}\n")
        if count:
            self.txt_btn.configure(state="normal")
        else:
            self.txt_btn.configure(state="disabled")
            self.txt_log.insert("end", "⚠️ В папке нет HTML файлов!\n")

    def start_txt_export(self):
        if not hasattr(self, 'txt_folder'):
            return
        self.txt_btn.configure(state="disabled")
        threading.Thread(
            target=self.run_txt_export,
            args=(self.txt_clean_var.get(), self.txt_split_var.get()),
            daemon=True).start()

    def run_txt_export(self, do_clean, do_split):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.txt_output = os.path.join(
            self.txt_folder, f"Chat_Export_{ts}.txt")
        try:
            gen = self.txt_exporter.export_stream(
                self.txt_folder, self.txt_output,
                remove_service=do_clean,
                max_size_mb=5 if do_split else 99999)
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
            try:
                os.startfile(os.path.dirname(self.txt_output))
            except:
                pass
        else:
            self.txt_log.insert("end", f"❌ Ошибка: {data}\n")

if __name__ == "__main__":
    app = TelegramMergerApp()
    app.mainloop()