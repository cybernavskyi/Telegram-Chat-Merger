import os
import sys
import glob
import webbrowser
import threading
import re
import time
import base64
import mimetypes
from datetime import datetime
from pathlib import Path

# UI & Logic libraries
import customtkinter as ctk
from tkinter import filedialog, messagebox
from bs4 import BeautifulSoup, FeatureNotFound
import pikepdf

# --- КОНФИГУРАЦИЯ ---
VERSION = "4.6 (Contrast Fix)"
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
RE_CLEAN_COLON = re.compile(r':\s*\n\s+')
RE_CLEAN_SPACES = re.compile(r'\s+')
RE_CLEAN_FONT = re.compile(r'font-family\s*:\s*\n\s*')
RE_FILENAME_NUMS = re.compile(r'\d+')

# --- ЦВЕТОВАЯ ПАЛИТРА ---
C_TEXT_MAIN = ("#000000", "#FFFFFF")
C_TEXT_BTN = "#FFFFFF"          # Белый текст (для главных цветных кнопок)
C_TEXT_SEC = ("#1A1A1A", "#FFFFFF") # Адаптивный текст (Черный в Light, Белый в Dark)
C_TEXT_DISABLED = "#EEEEEE"     
C_BG_MAIN = ("#F0F0F0", "#121212")
C_DROP_BG = ("#FFFFFF", "#2B2B2B")

C_BTN_PRI_BG = ("#0060C0", "#1473E6") 
C_BTN_PRI_HOVER = ("#004E9C", "#0D62C9")

C_BTN_WARN_BG = ("#D13438", "#D13438")
C_BTN_WARN_HOVER = ("#A4262C", "#A4262C")

C_BTN_SEC_BG = ("#E0E0E0", "#3A3A3A")
C_BTN_SEC_HOVER = ("#D0D0D0", "#4A4A4A")

C_BTN_PDF_BG = ("#2D7D9A", "#2D7D9A")
C_BTN_PDF_HOVER = ("#205A6F", "#205A6F")

# --- ENGINE 1 (HTML MERGE) ---
class MergerEngine:
    @staticmethod
    def clean_html_content(html_content):
        try:
            html_content = RE_CLEAN_COLON.sub(': ', html_content)
            html_content = RE_CLEAN_SPACES.sub(' ', html_content)
            html_content = RE_CLEAN_FONT.sub('font-family: ', html_content)
            return html_content
        except Exception:
            return html_content

    @staticmethod
    def custom_telegram_sort(file_path):
        filename = Path(file_path).name.lower()
        if filename == 'messages.html': return (0, '')
        numbers = RE_FILENAME_NUMS.findall(filename)
        if numbers: return (1, int(numbers[0]))
        return (2, filename)

    def process_images_to_base64(self, soup, root_folder):
        images = soup.find_all('img')
        if not images: return False
        for img in images:
            src = img.get('src')
            if not src or src.startswith(('data:', 'http')): continue
            try:
                import urllib.parse
                src = urllib.parse.unquote(src)
            except: pass
            
            img_path = os.path.join(root_folder, src)
            if os.path.isfile(img_path):
                try:
                    mime_type, _ = mimetypes.guess_type(img_path)
                    if not mime_type: mime_type = 'image/jpeg'
                    with open(img_path, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        img['src'] = f"data:{mime_type};base64,{encoded_string}"
                except: pass
        return True

    def advanced_cleanup(self, soup, remove_service=True):
        removed_count = 0
        if remove_service:
            for msg in soup.find_all(class_='service'):
                msg.decompose()
                removed_count += 1
        for reply in soup.find_all(class_='reply_to_details'):
            reply.decompose()
            removed_count += 1
        for avatar in soup.find_all(class_='userpic'):
            avatar.decompose()
        return removed_count

    def get_header(self, is_dark_mode=False):
        if is_dark_mode:
            colors = {'bg': '#000000', 'text': '#FFFFFF', 'card_bg': '#1A1A1A', 'card_border': '#505050', 'sep_color': '#64b5f6', 'sep_base_bg': '#263238'}
            extra_css = f'body, p, span, div {{ color: {colors["text"]} !important; }} a {{ color: {colors["sep_color"]} !important; }}'
        else:
            colors = {'bg': '#FFFFFF', 'text': '#000000', 'card_bg': '#F9F9F9', 'card_border': '#000000', 'sep_color': '#005A9E', 'sep_base_bg': '#EEFFFE'}
            extra_css = f'a {{ color: {colors["sep_color"]} !important; }}'

        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Merged Telegram Chat</title>
    <style>
        body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: {colors['bg']}; color: {colors['text']} !important; }}
        .chat-section {{ background: {colors['card_bg']}; border: 1px solid {colors['card_border']}; border-radius: 8px; padding: 15px; margin-bottom: 15px; page-break-inside: avoid; }}
        .file-separator {{ border-top: 2px solid {colors['sep_color']}; margin: 20px 0; padding-top: 10px; color: {colors['sep_color']}; font-weight: bold; page-break-after: avoid; }}
        .file-separator.base {{ background: {colors['sep_base_bg']}; padding: 10px; border-radius: 4px; }}
        .body {{ margin-left: 0 !important; }} 
        .from_name {{ font-weight: bold; color: {colors['sep_color']}; }}
        @media print {{ 
            .no-print {{ display: none !important; }} 
            body {{ background: white !important; color: black !important; margin: 0; padding: 0; }} 
            .chat-section {{ border: 1px solid #ccc !important; page-break-inside: avoid; }}
        }}
        img {{ max-width: 100%; height: auto; }}
        .error-msg {{ color: red; font-weight: bold; }}
        {extra_css}
    </style>
</head>
<body>
    <h1 class="no-print">📱 Объединенный чат Telegram</h1>
    <p class="no-print" style="font-size: 0.9em">Сгенерировано: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
'''

    def merge_stream(self, folder_path, output_path, embed_media=False, clean_service=False, is_dark=False):
        start_time = time.time()
        html_files = glob.glob(os.path.join(folder_path, "*.html"))
        if not html_files: raise FileNotFoundError("HTML файлы не найдены")
        sorted_files = sorted(html_files, key=self.custom_telegram_sort)
        total_files = len(sorted_files)
        
        parser = 'lxml'
        try: BeautifulSoup("", 'lxml')
        except FeatureNotFound: parser = 'html.parser'
        yield (0, f"🚀 Engine: {parser} | Clean: {clean_service}")

        try:
            with open(output_path, 'w', encoding='utf-8', errors='xmlcharrefreplace') as outfile:
                outfile.write(self.get_header(is_dark_mode=is_dark))
                success_count = 0
                removed_msg_count = 0
                
                for i, file_path in enumerate(sorted_files, 1):
                    filename = Path(file_path).name
                    yield (i / total_files, f"Обработка [{i}/{total_files}]: {filename}")
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            raw_html = infile.read()
                        cleaned = self.clean_html_content(raw_html)
                        soup = BeautifulSoup(cleaned, parser)
                        
                        removed_msg_count += self.advanced_cleanup(soup, remove_service=clean_service)
                        if embed_media: self.process_images_to_base64(soup, os.path.dirname(file_path))

                        body = soup.find('body')
                        sep_class = 'file-separator base' if filename.lower() == 'messages.html' else 'file-separator'
                        outfile.write(f'<div class="{sep_class}">📄 {filename}</div>\n<div class="chat-section">\n')
                        if body:
                            content = body.decode_contents() if hasattr(body, 'decode_contents') else str(body)
                            content = content.replace('<body>', '').replace('</body>', '')
                            outfile.write(content)
                        else: outfile.write(f'<div class="error-msg">⚠️ Пустой: {filename}</div>')
                        outfile.write('\n</div>\n')
                        success_count += 1
                    except Exception as e:
                        outfile.write(f'<div class="error-msg">❌ Ошибка {filename}: {e}</div>')
                outfile.write('</body></html>')
            
            elapsed = round(time.time() - start_time, 2)
            return True, (success_count, removed_msg_count, elapsed, parser)
        except Exception as e: return False, str(e)

# --- ENGINE 2 (SPLITTER) ---
class SplitterEngine:
    def split_pdf(self, input_path, max_size_mb=190):
        import io, gc
        try:
            pdf = pikepdf.open(input_path, suppress_warnings=True)
            total_pages = len(pdf.pages)
            base_name = os.path.splitext(input_path)[0]
            chunk_num = 1
            created_files = []
            limit_bytes = max_size_mb * 1024 * 1024
            CHECK_INTERVAL = 20 
            current_pdf = pikepdf.new()
            pages_buffer = [] 
            
            yield (0, f"Анализ {total_pages} страниц...")
            for i, page in enumerate(pdf.pages):
                current_pdf.pages.append(page)
                pages_buffer.append(page)
                if len(pages_buffer) >= CHECK_INTERVAL or i == total_pages - 1:
                    temp_buffer = io.BytesIO()
                    current_pdf.save(temp_buffer)
                    current_size = temp_buffer.tell()
                    if current_size > limit_bytes:
                        del current_pdf.pages[-len(pages_buffer):]
                        if len(current_pdf.pages) == 0:
                             yield (0, f"⚠️ Страница {i+1} > {max_size_mb}Мб!")
                             current_pdf.pages.append(pages_buffer[0])
                             pages_buffer = pages_buffer[1:] 
                        output_filename = f"{base_name}_part{chunk_num}.pdf"
                        current_pdf.save(output_filename)
                        created_files.append(output_filename)
                        yield ((i+1)/total_pages, f"💾 Сохранен Part {chunk_num}")
                        chunk_num += 1
                        current_pdf.close()
                        del current_pdf
                        gc.collect()
                        current_pdf = pikepdf.new()
                        for buffered_page in pages_buffer: current_pdf.pages.append(buffered_page)
                    pages_buffer = []
            if len(current_pdf.pages) > 0:
                output_filename = f"{base_name}_part{chunk_num}.pdf"
                current_pdf.save(output_filename)
                created_files.append(output_filename)
                yield (1.0, f"💾 Финал: Part {chunk_num}")
            pdf.close()
            return True, created_files
        except Exception as e: return False, f"Ошибка: {str(e)}"

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
        self.merger = MergerEngine()
        self.splitter = SplitterEngine()
        self.setup_window()
        self.create_ui()

    def setup_window(self):
        self.title(f"Telegram Merger v{VERSION}")
        self.geometry("800x600") 
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
        self.tab_merge = self.tabview.add("1. HTML Merger")
        self.tab_split = self.tabview.add("2. PDF Splitter")
        self.setup_merge_tab()
        self.setup_split_tab()

        # FOOTER
        self.footer_lbl = ctk.CTkLabel(
            self, 
            text="© HardCore Affiliate Club, 2025",
            font=("Segoe UI", 12, "underline"),
            text_color=C_BTN_PRI_BG[1], 
            cursor="hand2"
        )
        self.footer_lbl.grid(row=2, column=0, pady=(0, 10))
        self.footer_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/hardcoreaffiliateclub"))

    def change_theme(self, new_theme: str): ctk.set_appearance_mode(new_theme)

    def setup_merge_tab(self):
        t = self.tab_merge
        t.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(t, text="Шаг 1: Создание или загрузка HTML", font=("Segoe UI", 20, "bold"), text_color=C_TEXT_MAIN).pack(pady=(10,5))
        
        self.m_drop = ctk.CTkLabel(t, text="📁 Перетащи папку чата\nИЛИ готовый файл HTML", 
                                 fg_color=C_DROP_BG, text_color=C_TEXT_MAIN, height=90, corner_radius=8)
        self.m_drop.pack(fill="x", padx=20, pady=5)
        
        if DND_AVAILABLE:
            self.m_drop.drop_target_register(DND_FILES)
            self.m_drop.dnd_bind('<<Drop>>', self.on_drop_merge)
        self.m_drop.bind("<Button-1>", lambda e: self.select_folder_merge())

        # CONTROL AREA
        self.control_area_merge = ctk.CTkFrame(t, fg_color="transparent", height=75)
        self.control_area_merge.pack(fill="x", padx=20, pady=0)
        self.control_area_merge.pack_propagate(False)

        btn_frame = ctk.CTkFrame(self.control_area_merge, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 5))
        
        # ИСПОЛЬЗУЕМ C_TEXT_SEC ЗДЕСЬ (Адаптивный цвет текста)
        ctk.CTkButton(btn_frame, text="Выбрать папку", command=self.select_folder_merge, 
                      width=150, fg_color=C_BTN_SEC_BG, hover_color=C_BTN_SEC_HOVER, text_color=C_TEXT_SEC).pack(side="left", padx=(0,5))
        ctk.CTkButton(btn_frame, text="Выбрать HTML файл", command=self.select_file_html_merge, 
                      width=150, fg_color=C_BTN_SEC_BG, hover_color=C_BTN_SEC_HOVER, text_color=C_TEXT_SEC).pack(side="right", padx=(5,0))

        opt_frame = ctk.CTkFrame(self.control_area_merge, fg_color="transparent")
        opt_frame.pack(fill="x", pady=0)
        self.embed_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt_frame, text="Встроить картинки в HTML", variable=self.embed_var, text_color=C_TEXT_MAIN).pack(side="left", padx=(0, 20))
        self.clean_service_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_frame, text="Удалить сервисные сообщения", variable=self.clean_service_var, text_color=C_TEXT_MAIN).pack(side="left")
        
        # MAIN ACTIONS (Остаются белыми)
        self.m_btn = ctk.CTkButton(t, text="СОЗДАТЬ MERGED HTML", state="disabled", command=self.start_merge, height=45,
            font=("Segoe UI", 14, "bold"), fg_color=C_BTN_PRI_BG, hover_color=C_BTN_PRI_HOVER, 
            text_color=C_TEXT_BTN, text_color_disabled=C_TEXT_DISABLED)
        self.m_btn.pack(fill="x", padx=20, pady=(10, 5))
        
        self.m_pdf = ctk.CTkButton(t, text="🖨️ Открыть в браузере для создания PDF", state="disabled", command=self.manual_print_instruction,
            height=45, fg_color=C_BTN_PDF_BG, hover_color=C_BTN_PDF_HOVER, 
            text_color=C_TEXT_BTN, text_color_disabled=C_TEXT_DISABLED)
        self.m_pdf.pack(fill="x", padx=20, pady=5)

        self.m_log = ctk.CTkTextbox(t, height=80, text_color=C_TEXT_MAIN, fg_color=C_DROP_BG)
        self.m_log.pack(fill="x", padx=20, pady=10)
        self.m_progress = ctk.CTkProgressBar(t, progress_color=C_BTN_PRI_BG[0])
        self.m_progress.pack(fill="x", padx=20, pady=(0,10))
        self.m_progress.set(0)

    def setup_split_tab(self):
        t = self.tab_split
        t.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(t, text="Шаг 2: Нарезка большого PDF для NotebookLM", font=("Segoe UI", 20, "bold"), text_color=C_TEXT_MAIN).pack(pady=(10,5))
        
        self.s_drop = ctk.CTkLabel(t, text="📄 Перетащи PDF файл сюда", 
                                 fg_color=C_DROP_BG, text_color=C_TEXT_MAIN, height=90, corner_radius=8)
        self.s_drop.pack(fill="x", padx=20, pady=5)
        if DND_AVAILABLE:
            self.s_drop.drop_target_register(DND_FILES)
            self.s_drop.dnd_bind('<<Drop>>', self.on_drop_split)
        self.s_drop.bind("<Button-1>", lambda e: self.select_file_split())

        self.control_area_split = ctk.CTkFrame(t, fg_color="transparent", height=75)
        self.control_area_split.pack(fill="x", padx=20, pady=0)
        self.control_area_split.pack_propagate(False) 

        self.s_btn = ctk.CTkButton(t, text="РАЗДЕЛИТЬ (LIMIT 190MB)", state="disabled", command=self.start_split, height=45, 
            font=("Segoe UI", 14, "bold"), fg_color=C_BTN_WARN_BG, hover_color=C_BTN_WARN_HOVER, 
            text_color=C_TEXT_BTN, text_color_disabled=C_TEXT_DISABLED)
        self.s_btn.pack(fill="x", padx=20, pady=(10, 5))

        self.s_log = ctk.CTkTextbox(t, height=135, text_color=C_TEXT_MAIN, fg_color=C_DROP_BG)
        self.s_log.pack(fill="x", padx=20, pady=10)
        self.s_progress = ctk.CTkProgressBar(t, progress_color=C_BTN_WARN_BG[0])
        self.s_progress.pack(fill="x", padx=20, pady=(0,10))
        self.s_progress.set(0)

    # --- HANDLERS ---
    def clean_path(self, data): return data.strip().strip('{}').strip('"')
    def on_drop_merge(self, event): self.load_merge_source(self.clean_path(event.data))
    def select_folder_merge(self): 
        p = filedialog.askdirectory()
        if p: self.load_merge_source(p)
    def select_file_html_merge(self):
        p = filedialog.askopenfilename(filetypes=[("HTML Files", "*.html")])
        if p: self.load_merge_source(p)

    def load_merge_source(self, path):
        if os.path.isdir(path):
            self.merge_folder = path
            count = len(glob.glob(os.path.join(path, "*.html")))
            self.m_drop.configure(text=f"📂 Папка: {Path(path).name}\nНайдено HTML файлов: {count}")
            self.m_log.insert("end", f"📂 Загружена папка: {path}\n")
            if count: 
                self.m_btn.configure(state="normal", text="СОЗДАТЬ MERGED HTML")
                self.m_pdf.configure(state="disabled")
            else:
                self.m_btn.configure(state="disabled")
                self.m_log.insert("end", "⚠️ В папке нет HTML файлов!\n")
        elif os.path.isfile(path) and path.lower().endswith('.html'):
            self.html_output = path
            self.m_drop.configure(text=f"📄 Файл: {Path(path).name}\n(Готов к печати)")
            self.m_log.insert("end", f"📄 Загружен файл: {Path(path).name}\n")
            self.m_btn.configure(state="disabled", text="HTML файл выбран")
            self.m_pdf.configure(state="normal")
            self.m_progress.set(1.0)

    def start_merge(self):
        self.m_btn.configure(state="disabled")
        self.m_pdf.configure(state="disabled")
        is_dark = ctk.get_appearance_mode() == "Dark"
        threading.Thread(target=self.run_merge, args=(self.embed_var.get(), self.clean_service_var.get(), is_dark), daemon=True).start()

    def run_merge(self, do_embed, do_clean, is_dark):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.html_output = os.path.join(self.merge_folder, f"Full_Chat_{ts}.html")
        try:
            gen = self.merger.merge_stream(self.merge_folder, self.html_output, embed_media=do_embed, clean_service=do_clean, is_dark=is_dark)
            while True:
                item = next(gen)
                self.after(0, lambda v=item: self.m_progress.set(v[0]))
        except StopIteration as e: self.after(0, lambda r=e.value: self.finish_merge(r))
        except Exception as e: self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def finish_merge(self, result):
        success, data = result
        self.m_btn.configure(state="normal")
        if success:
            self.m_pdf.configure(state="normal")
            self.m_progress.set(1.0)
            count, removed, tm, _ = data
            msg = f"✅ HTML создан! {count} файлов за {tm} сек.\nФайл: {Path(self.html_output).name}\n"
            if removed: msg += f"🗑 Очищено: {removed} элементов\n"
            self.m_log.insert("end", msg)
            self.m_log.see("end")
            messagebox.showinfo("Готово", f"HTML файл готов!\n\n{Path(self.html_output).name}")

    def manual_print_instruction(self):
        if not hasattr(self, 'html_output') or not os.path.exists(self.html_output): return
        webbrowser.open(f'file:///{self.html_output}')
        msg = (
            "✅ Файл открыт в вашем браузере.\n\n"
            "ЧТОБЫ СОХРАНИТЬ КАК PDF:\n"
            "1. Нажмите Ctrl + P (Печать)\n"
            "2. В поле 'Принтер' выберите 'Сохранить как PDF'\n"
            "3. Нажмите 'Сохранить'\n\n"
            "💡 Совет: Отключите 'Колонтитулы' в настройках печати для чистого вида."
        )
        messagebox.showinfo("Инструкция по PDF", msg)
        self.m_log.insert("end", "🖨️ Запущен процесс ручной печати.\n")

    def on_drop_split(self, event):
        f = self.clean_path(event.data)
        if f.lower().endswith('.pdf'): self.load_pdf(f)
    def select_file_split(self):
        f = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if f: self.load_pdf(f)
    def load_pdf(self, path):
        self.pdf_input = path
        size_mb = os.path.getsize(path) / (1024*1024)
        self.s_drop.configure(text=f"📄 {Path(path).name}\nРазмер: {size_mb:.1f} MB")
        self.s_btn.configure(state="normal")
        self.s_log.insert("end", f"Выбран файл: {Path(path).name}\n")

    def start_split(self):
        if not hasattr(self, 'pdf_input') or not os.path.exists(self.pdf_input): return
        file_size_mb = os.path.getsize(self.pdf_input) / (1024 * 1024)
        LIMIT_MB = 190
        if file_size_mb < LIMIT_MB:
            messagebox.showinfo("Нарезка не требуется", f"Файл весит всего {file_size_mb:.1f} МБ.\nНарезка нужна только если файл больше {LIMIT_MB} МБ.")
            return
        self.s_btn.configure(state="disabled")
        threading.Thread(target=self.run_split, daemon=True).start()

    def run_split(self):
        try:
            gen = self.splitter.split_pdf(self.pdf_input)
            while True:
                item = next(gen)
                self.after(0, lambda v=item: self.update_ui_split(v))
        except StopIteration as e: self.after(0, lambda r=e.value: self.finish_split(r))
    def update_ui_split(self, item):
        self.s_progress.set(item[0])
        if "💾" in item[1] or "⚠️" in item[1]:
            self.s_log.insert("end", item[1] + "\n")
            self.s_log.see("end")
    def finish_split(self, result):
        self.s_btn.configure(state="normal")
        self.s_progress.set(1.0)
        if result[0]: 
            self.s_log.insert("end", "✅ PDF успешно нарезан!\n")
            messagebox.showinfo("Успех", "PDF нарезан на части <190MB")
            try: os.startfile(os.path.dirname(result[1][0]))
            except: pass
        else: 
            self.s_log.insert("end", f"❌ {result[1]}\n")

if __name__ == "__main__":
    app = TelegramMergerApp()
    app.mainloop()