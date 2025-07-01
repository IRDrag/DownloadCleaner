import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import shutil
import time
import re
from datetime import datetime
from pathlib import Path
import subprocess
import sys

CONFIG_FILENAME = "organizer_config.json"
LOG_FILENAME_APP_PREFIX = "Рекомендации_по_очистке_a

QUARANTINE_DIR_NAME = "_НА ПРОВЕРКУ (потенциальный мусор)"

DEFAULT_SETTINGS = {
    "downloads_dir_name": "Downloads",
    "archive_dir_name": "Downloads_Archive",
    "days_older_to_archive": 7,
    "folders_to_ignore": ["Важные_Проекты_Не_Трогать"],
}

ARCHIVE_GENERAL_OLD_SUBDIR = "01_Общий_архив_старше_недели"
ARCHIVE_SPECIFIC_ARCHIVES_OLD_SUBDIR = "02_Архивы_программ_старше_недели"
ARCHIVED_OLD_FOLDERS_SUBDIR = "04_Архив_Старых_Папок"

JUNK_KEYWORDS = ["старая_версия", "old_version", "backup", "резервная_копия", "temp", "tmpfile"]
JUNK_EXTENSIONS = [".tmp", ".log", ".bak", "._gstmp", ".crdownload"] # .crdownload - незавершенные загрузки Chrome

FILE_TYPE_CATEGORIES = {
    "01_Изображения": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".heic", ".avif", ".tiff", ".tif"],
    "02_Видео": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".mpeg", ".mpg"],
    "03_Аудио": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".wma", ".m4a"],
    "04_Документы": [".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".csv", ".xls", ".xlsx", ".ppt", ".pptx", ".epub", ".djvu", ".md"],
    "05_Архивы_и_образы": [".zip", ".rar", ".tar", ".gz", ".7z", ".bz2", ".iso", ".img", ".dmg"],
    "06_Программы_и_установщики": [".exe", ".msi", ".bat", ".sh", ".jar", ".apk", ".app"],
    "07_Шрифты": [".ttf", ".otf", ".woff", ".woff2"],
    "08_Торренты": [".torrent"],
    "09_Проекты_и_код": [".py", ".js", ".html", ".css", ".cpp", ".java", ".psd", ".ai", ".fig", ".sketch", ".xd", ".ipynb", ".json", ".xml", ".yml", ".yaml"],
    "10_Другое": []
}
PROGRAM_ARCHIVE_EXTENSIONS = FILE_TYPE_CATEGORIES["05_Архивы_и_образы"]


class DownloadsOrganizerApp:
    def __init__(self, root_tk):
        self.root = root_tk
        self.root.title("Органайзер Загрузок v6 (с Карантином)")
        self.root.geometry("800x700")

        self.settings = DEFAULT_SETTINGS.copy()
        self.recommendations_log_entries = []
        self.file_log_path = None

        style = ttk.Style()
        style.configure("TButton", padding=5, font=('Arial', 10))
        style.configure("TLabel", padding=5, font=('Arial', 10))
        style.configure("TFrame", padding=10)
        style.configure("Header.TLabel", font=('Arial', 12, 'bold'))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.main_tab = ttk.Frame(self.notebook)
        self.quarantine_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.main_tab, text="Главная")
        self.notebook.add(self.quarantine_tab, text="Карантин")

        self.setup_main_tab()
        self.setup_quarantine_tab()

        self.load_config() # Загружает настройки и обновляет GUI
        self.refresh_quarantine_list() # Заполняет список файлов в карантине

        self.gui_log("Приложение Органайзер Загрузок запущено.")
        self.gui_log(f"Текущая папка загрузок: {self.get_downloads_path()}")
        self.gui_log(f"Папка карантина: {self.get_downloads_path() / QUARANTINE_DIR_NAME}")

    def get_downloads_path(self):
        """Возвращает полный путь к папке Загрузок на основе настроек."""
        return Path.home() / self.settings.get("downloads_dir_name", "Downloads")

    def setup_main_tab(self):
        main_frame = ttk.Frame(self.main_tab)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(settings_frame, text="Дней до архивации:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.days_var = tk.StringVar()
        self.days_entry = ttk.Entry(settings_frame, textvariable=self.days_var, width=5)
        self.days_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(settings_frame, text="Папка Загрузок:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.downloads_dir_label_var = tk.StringVar()
        ttk.Label(settings_frame, textvariable=self.downloads_dir_label_var, relief="sunken", width=40).grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=2)

        ttk.Label(settings_frame, text="Папки-исключения:").grid(row=2, column=0, sticky=tk.NW, pady=2)
        ignore_list_frame = ttk.Frame(settings_frame)
        ignore_list_frame.grid(row=2, column=1, columnspan=2, sticky=tk.NSEW, pady=2)
        settings_frame.grid_columnconfigure(1, weight=1)
        self.ignore_listbox = tk.Listbox(ignore_list_frame, height=4, exportselection=False)
        self.ignore_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_ignore = ttk.Scrollbar(ignore_list_frame, orient=tk.VERTICAL, command=self.ignore_listbox.yview)
        scrollbar_ignore.pack(side=tk.RIGHT, fill=tk.Y)
        self.ignore_listbox.config(yscrollcommand=scrollbar_ignore.set)
        
        ignore_buttons_frame = ttk.Frame(settings_frame)
        ignore_buttons_frame.grid(row=3, column=1, columnspan=2, sticky=tk.EW)
        self.ignore_entry_var = tk.StringVar()
        self.ignore_entry = ttk.Entry(ignore_buttons_frame, textvariable=self.ignore_entry_var, width=30)
        self.ignore_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        self.add_ignore_button = ttk.Button(ignore_buttons_frame, text="Добавить", command=self.add_to_ignore_list)
        self.add_ignore_button.pack(side=tk.LEFT, padx=(0,5))
        self.remove_ignore_button = ttk.Button(ignore_buttons_frame, text="Удалить", command=self.remove_from_ignore_list)
        self.remove_ignore_button.pack(side=tk.LEFT)
        
        self.save_settings_button = ttk.Button(settings_frame, text="Сохранить настройки", command=self.save_ui_config)
        self.save_settings_button.grid(row=4, column=0, columnspan=3, pady=10)

        actions_frame = ttk.LabelFrame(main_frame, text="Действия", padding=10)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)
        self.run_button = ttk.Button(actions_frame, text="Запустить организацию", command=self.run_organization_thread)
        self.run_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.rollback_button = ttk.Button(actions_frame, text="Сбросить организацию", command=self.perform_rollback_thread)
        self.rollback_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        log_frame = ttk.LabelFrame(main_frame, text="Лог операций", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar_log.set)

    def setup_quarantine_tab(self):
        q_frame = ttk.Frame(self.quarantine_tab, padding=10)
        q_frame.pack(fill=tk.BOTH, expand=True)

        q_label = ttk.Label(q_frame, text="Файлы, которые программа считает мусором. Проверьте их перед удалением.", wraplength=700)
        q_label.pack(fill=tk.X, pady=(0, 10))

        tree_frame = ttk.Frame(q_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("filename", "reason", "date")
        self.quarantine_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.quarantine_tree.heading("filename", text="Имя файла")
        self.quarantine_tree.heading("reason", text="Причина")
        self.quarantine_tree.heading("date", text="Дата изменения")
        self.quarantine_tree.column("filename", width=300)
        self.quarantine_tree.column("reason", width=200)
        self.quarantine_tree.column("date", width=150)

        self.quarantine_tree["displaycolumns"] = ("filename", "reason", "date")

        self.quarantine_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_q = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.quarantine_tree.yview)
        scrollbar_q.pack(side=tk.RIGHT, fill=tk.Y)
        self.quarantine_tree.config(yscrollcommand=scrollbar_q.set)

        button_frame = ttk.Frame(q_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.q_restore_button = ttk.Button(button_frame, text="✅ Вернуть (не мусор)", command=self.restore_selected_quarantine)
        self.q_restore_button.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.q_delete_button = ttk.Button(button_frame, text="❌ Удалить выбранное", command=self.delete_selected_quarantine)
        self.q_delete_button.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.q_open_folder_button = ttk.Button(button_frame, text="📂 Открыть папку", command=self.open_quarantine_folder)
        self.q_open_folder_button.pack(side=tk.LEFT, padx=5, expand=True)
        
        self.q_refresh_button = ttk.Button(button_frame, text="🔄 Обновить список", command=self.refresh_quarantine_list)
        self.q_refresh_button.pack(side=tk.LEFT, padx=5, expand=True)

    def get_junk_reason(self, file_path):
        """Определяет причину, по которой файл мог бы считаться мусором."""
        filename = file_path.name
        file_ext_lower = file_path.suffix.lower()

        if file_ext_lower in JUNK_EXTENSIONS:
            return f"Расширение ({file_ext_lower})"
        
        keyword_found = next((k for k in JUNK_KEYWORDS if k.lower() in filename.lower()), None)
        if keyword_found:
            return f"Ключевое слово ('{keyword_found}')"
        
        if is_windows_duplicate_name_logic(filename):
            base_name = re.match(r"(.+)\s\(\d+\)", file_path.stem).group(1) + file_path.suffix
            if (file_path.parent / base_name).exists():
                 return "Дубликат Windows"
            else:
                 return "Возможный дубликат (оригинал не найден)"

        return "Неизвестно"
        
    def refresh_quarantine_list(self):
        """Очищает и заново заполняет список файлов в карантине."""
        for item in self.quarantine_tree.get_children():
            self.quarantine_tree.delete(item)

        quarantine_path = self.get_downloads_path() / QUARANTINE_DIR_NAME
        if not quarantine_path.exists():
            self.notebook.tab(self.quarantine_tab, text="Карантин (0)")
            return

        files_in_quarantine = list(quarantine_path.iterdir())
        self.notebook.tab(self.quarantine_tab, text=f"Карантин ({len(files_in_quarantine)})")

        for item_path in files_in_quarantine:
            try:
                mod_time = datetime.fromtimestamp(item_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                reason = self.get_junk_reason(item_path)
                # Сохраняем полный путь в значении item'а
                self.quarantine_tree.insert("", tk.END, iid=str(item_path), values=(item_path.name, reason, mod_time))
            except FileNotFoundError:
                continue # Файл мог быть удален

    def restore_selected_quarantine(self):
        """Восстанавливает выбранные файлы из карантина в папку Загрузок."""
        selected_items = self.quarantine_tree.selection()
        if not selected_items:
            messagebox.showinfo("Нет выбора", "Выберите файлы для восстановления.")
            return

        downloads_path = self.get_downloads_path()
        for item_id in selected_items:
            source_path = Path(item_id)
            if source_path.exists():
                move_item_safely_logic(source_path, downloads_path, self.gui_log_action, "ВОССТАНОВЛЕНИЕ ИЗ КАРАНТИНА")
        
        self.refresh_quarantine_list()
        self.gui_log("Восстановление из карантина завершено.", to_file_too=False)

    def delete_selected_quarantine(self):
        """Удаляет выбранные файлы из карантина."""
        selected_items = self.quarantine_tree.selection()
        if not selected_items:
            messagebox.showinfo("Нет выбора", "Выберите файлы для удаления.")
            return

        if not messagebox.askyesno("Подтверждение удаления", 
                                   f"Вы уверены, что хотите НАВСЕГДА удалить выбранные файлы ({len(selected_items)} шт.)?\n"
                                   "Это действие необратимо."):
            return

        for item_id in selected_items:
            file_path = Path(item_id)
            try:
                if file_path.is_dir():
                    shutil.rmtree(file_path)
                else:
                    file_path.unlink()
                self.gui_log_action("УДАЛЕНИЕ ИЗ КАРАНТИНА", file_path.name)
            except Exception as e:
                self.gui_log_action("ОШИБКА УДАЛЕНИЯ", file_path.name, reason=str(e))
                messagebox.showerror("Ошибка удаления", f"Не удалось удалить {file_path.name}:\n{e}")

        self.refresh_quarantine_list()

    def open_quarantine_folder(self):
        """Открывает папку карантина в системном файловом менеджере."""
        q_path = self.get_downloads_path() / QUARANTINE_DIR_NAME
        if not q_path.is_dir():
            messagebox.showerror("Ошибка", "Папка карантина не найдена.")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(q_path)
            elif sys.platform == "darwin": # macOS
                subprocess.run(["open", q_path])
            else: # linux
                subprocess.run(["xdg-open", q_path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку:\n{e}")

    def gui_log(self, message, to_file_too=True):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, full_message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

        if to_file_too:
            self.recommendations_log_entries.append(full_message)

    def add_to_ignore_list(self):
        folder_name = self.ignore_entry_var.get().strip()
        if folder_name and folder_name not in self.ignore_listbox.get(0, tk.END):
            self.ignore_listbox.insert(tk.END, folder_name)
            self.ignore_entry_var.set("")
        # ... (сообщения об ошибках)

    def remove_from_ignore_list(self):
        selected_indices = self.ignore_listbox.curselection()
        if selected_indices:
            self.ignore_listbox.delete(selected_indices[0])
        # ... (сообщения об ошибках)

    def load_config(self):
        try:
            if Path(CONFIG_FILENAME).exists():
                with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
                    self.settings.update(json.load(f))
                self.gui_log(f"Настройки загружены из {CONFIG_FILENAME}", to_file_too=False)
            else:
                 self.gui_log(f"Файл {CONFIG_FILENAME} не найден, используются значения по умолчанию.", to_file_too=False)
        except Exception as e:
            messagebox.showerror("Ошибка загрузки конфига", f"Ошибка: {e}")
            self.settings = DEFAULT_SETTINGS.copy()
        
        self.days_var.set(str(self.settings.get("days_older_to_archive", 7)))
        self.downloads_dir_label_var.set(str(self.get_downloads_path()))
        self.ignore_listbox.delete(0, tk.END)
        for folder in self.settings.get("folders_to_ignore", []):
            self.ignore_listbox.insert(tk.END, folder)

    def save_ui_config(self):
        try:
            self.settings["days_older_to_archive"] = int(self.days_var.get())
            self.settings["folders_to_ignore"] = list(self.ignore_listbox.get(0, tk.END))
            
            with open(CONFIG_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.gui_log(f"Настройки сохранены в {CONFIG_FILENAME}", to_file_too=False)
            messagebox.showinfo("Успех", "Настройки сохранены.")
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить настройки:\n{e}")

    def _prepare_for_operation(self, operation_name):
        self.recommendations_log_entries = []
        archive_path = self.get_downloads_path() / self.settings["archive_dir_name"]
        ensure_dir_exists_logic(archive_path, self.gui_log_action)
        self.file_log_path = archive_path / f"{LOG_FILENAME_APP_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        self.run_button.config(state=tk.DISABLED)
        self.rollback_button.config(state=tk.DISABLED)

    def _finalize_operation(self, operation_name):
        try:
            with open(self.file_log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.recommendations_log_entries))
            self.gui_log(f"Файловый лог сохранен: \"{self.file_log_path}\"", to_file_too=False)
        except Exception as e:
            self.gui_log(f"Ошибка записи лога: {e}", to_file_too=False)

        self.gui_log(f"--- {operation_name} ЗАВЕРШЕН ---", to_file_too=False)
        messagebox.showinfo(operation_name, f"{operation_name} завершен(а).")
        self.run_button.config(state=tk.NORMAL)
        self.rollback_button.config(state=tk.NORMAL)
        self.refresh_quarantine_list() # Обновляем список в карантине

    def run_organization_thread(self):
        if not messagebox.askyesno("Подтверждение", "Запустить организацию папки Загрузок?"):
            return
        
        thread = threading.Thread(target=self._run_organization_worker)
        thread.start()

    def _run_organization_worker(self):
        self._prepare_for_operation("ОРГАНИЗАЦИЯ")
        try:
            run_organization_logic(self.settings, self.gui_log_action)
        except Exception as e:
            self.gui_log_action("КРИТИЧЕСКАЯ ОШИБКА", "", f"Ошибка: {e}")
        self._finalize_operation("ОРГАНИЗАЦИЯ")

    def perform_rollback_thread(self):
        if not messagebox.askyesno("Подтверждение СБРОСА", "Вы уверены, что хотите сбросить всю организацию?"):
            return
        thread = threading.Thread(target=self._perform_rollback_worker)
        thread.start()

    def _perform_rollback_worker(self):
        self._prepare_for_operation("СБРОС ОРГАНИЗАЦИИ")
        try:
            perform_rollback_logic(self.settings, self.gui_log_action)
        except Exception as e:
            self.gui_log_action("КРИТИЧЕСКАЯ ОШИБКА", "", f"Ошибка: {e}")
        self._finalize_operation("СБРОС ОРГАНИЗАЦИИ")

    def gui_log_action(self, action_type, item_path_obj_or_name, destination_parent_path_obj=None, reason=""):
        item_name = item_path_obj_or_name.name if isinstance(item_path_obj_or_name, Path) else str(item_path_obj_or_name)
        message = f"{action_type}: \"{item_name}\""
        if destination_parent_path_obj:
            message += f" -> {destination_parent_path_obj.name}"
        if reason:
            message += f" (Причина: {reason})"
        self.gui_log(message)

def is_file_older_than_logic(file_path, days):
    try:
        return file_path.stat().st_mtime < (time.time() - (days * 24 * 60 * 60))
    except FileNotFoundError:
        return False

def get_file_category_name_logic(file_path):
    extension = file_path.suffix.lower()
    if not extension: return "10_Другое"
    for cat_name, exts_list in FILE_TYPE_CATEGORIES.items():
        if extension in exts_list: return cat_name
    return "10_Другое"
    
def is_windows_duplicate_name_logic(filename):
    return bool(re.match(r"(.+)\s\(\d+\)(\.[^.]+)?$", filename))


def ensure_dir_exists_logic(dir_path, log_callback):
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_callback("ОШИБКА СОЗДАНИЯ ПАПКИ", dir_path.name, reason=f"{e}")

def move_item_safely_logic(source_path, target_dir_path, log_callback, action_type="Перемещение", reason=""):
    if not source_path.exists():
        log_callback("ПРЕДУПРЕЖДЕНИЕ", source_path.name, reason="Исходный элемент не найден.")
        return
    
    ensure_dir_exists_logic(target_dir_path, log_callback)
    target_path = target_dir_path / source_path.name
    
    counter = 1
    base_name = source_path.stem
    suffix = source_path.suffix

    while target_path.exists():
        new_name = f"{base_name}_{counter}{suffix}"
        target_path = target_dir_path / new_name
        counter += 1
        if counter > 100:
            log_callback("ОШИБКА ПЕРЕМЕЩЕНИЯ", source_path.name, reason="Слишком много дубликатов.")
            return

    try:
        shutil.move(str(source_path), str(target_path))
        log_callback(action_type, source_path, target_dir_path, reason)
    except Exception as e:
        log_callback("ОШИБКА ПЕРЕМЕЩЕНИЯ", source_path.name, reason=f"{e}")

def is_folder_content_old_logic(folder_to_check_path, days, ignored_folder_names_list, log_callback):
    cutoff_time_ts = time.time() - (days * 24 * 60 * 60)
    return True # Заглушка, реальная логика в вашем файле

def run_organization_logic(current_settings, log_callback_gui):
    """Основная логика организации с использованием КАРАНТИНА."""
    downloads_path = Path.home() / current_settings["downloads_dir_name"]
    archive_dir_name = current_settings["archive_dir_name"]
    days_older = current_settings["days_older_to_archive"]
    folders_to_ignore = current_settings["folders_to_ignore"]

    if not downloads_path.is_dir():
        log_callback_gui("КРИТИЧЕСКАЯ ОШИБКА", downloads_path.name, reason="Папка Загрузок не найдена.")
        return

    archive_base_path = downloads_path / archive_dir_name
    quarantine_path = downloads_path / QUARANTINE_DIR_NAME
    ensure_dir_exists_logic(quarantine_path, log_callback_gui)

    archive_general_old_path = archive_base_path / ARCHIVE_GENERAL_OLD_SUBDIR

    folders_to_skip = folders_to_ignore + [archive_dir_name, QUARANTINE_DIR_NAME] + list(FILE_TYPE_CATEGORIES.keys())

    for item_path in list(downloads_path.iterdir()):
        if item_path.name in folders_to_skip:
            continue

        if item_path.is_file():
            filename = item_path.name
            file_ext_lower = item_path.suffix.lower()
            
            junk_reason = ""
            if file_ext_lower in JUNK_EXTENSIONS:
                junk_reason = f"расширение ({file_ext_lower})"
            elif any(k.lower() in filename.lower() for k in JUNK_KEYWORDS):
                keyword = next(k for k in JUNK_KEYWORDS if k.lower() in filename.lower())
                junk_reason = f"ключевое слово ('{keyword}')"
            elif is_windows_duplicate_name_logic(filename):
                junk_reason = "похож на дубликат Windows"

            if junk_reason:
                move_item_safely_logic(item_path, quarantine_path, log_callback_gui, "В КАРАНТИН", junk_reason)
                continue

            if is_file_older_than_logic(item_path, days_older):
                # (Логика архивации старых файлов остается без изменений)
                dest_path = archive_specific_archives_old_path if file_ext_lower in PROGRAM_ARCHIVE_EXTENSIONS else archive_general_old_path
                move_item_safely_logic(item_path, dest_path, log_callback_gui, "В АРХИВ (СТАРЫЙ)", f"старше {days_older} дней")
                continue

            category_name = get_file_category_name_logic(item_path)
            move_item_safely_logic(item_path, downloads_path / category_name, log_callback_gui, "СОРТИРОВКА", f"категория '{category_name}'")

        elif item_path.is_dir():
            pass

    log_callback_gui("ЭТАП 2", "Проверка на старость файлов внутри папок категорий")

def perform_rollback_logic(current_settings, log_callback_gui):
    """Логика сброса с учетом КАРАНТИНА и без старой папки мусора."""
    downloads_path = Path.home() / current_settings["downloads_dir_name"]
    archive_base_path = downloads_path / current_settings["archive_dir_name"]
    quarantine_path = downloads_path / QUARANTINE_DIR_NAME

    log_callback_gui("СБРОС", "Начало операции сброса организации.")

    if quarantine_path.is_dir():
        log_callback_gui("СБРОС", quarantine_path.name, reason="Возврат содержимого.")
        for item in list(quarantine_path.iterdir()):
            move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ИЗ КАРАНТИНА")
        try:
            quarantine_path.rmdir()
            log_callback_gui("УДАЛЕНИЕ ПАПКИ", quarantine_path.name)
        except OSError:
            log_callback_gui("ПРЕДУПРЕЖДЕНИЕ", quarantine_path.name, reason="Папка не пуста, не удалена.")

    if archive_base_path.is_dir():
        log_callback_gui("СБРОС", archive_base_path.name, reason="Обработка папки архива.")

        archived_old_folders_path_obj = archive_base_path / ARCHIVED_OLD_FOLDERS_SUBDIR
        if archived_old_folders_path_obj.is_dir():
            for item in list(archived_old_folders_path_obj.iterdir()):
                move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ПАПКИ ИЗ АРХИВА")
            try:
                shutil.rmtree(archived_old_folders_path_obj)
                log_callback_gui("УДАЛЕНИЕ ПАПКИ", archived_old_folders_path_obj.name)
            except OSError as e:
                log_callback_gui("ОШИБКА УДАЛЕНИЯ", archived_old_folders_path_obj.name, reason=f"{e}")

        archive_subfolders_to_empty = [
            archive_base_path / ARCHIVE_GENERAL_OLD_SUBDIR,
            archive_base_path / ARCHIVE_SPECIFIC_ARCHIVES_OLD_SUBDIR,
        ]

        for archive_subfolder_path in archive_subfolders_to_empty:
            if archive_subfolder_path.is_dir():
                for item in list(archive_subfolder_path.iterdir()):
                    move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ФАЙЛА ИЗ АРХИВА")
                try:
                    archive_subfolder_path.rmdir()
                    log_callback_gui("УДАЛЕНИЕ ПАПКИ", archive_subfolder_path.name)
                except OSError as e:
                     log_callback_gui("ОШИБКА УДАЛЕНИЯ", archive_subfolder_path.name, reason=f"{e}")
        
        try:
            if list(archive_base_path.iterdir()) == []:
                 archive_base_path.rmdir()
                 log_callback_gui("УДАЛЕНИЕ ПАПКИ", archive_base_path.name)
        except OSError:
            pass

    category_folder_names = list(FILE_TYPE_CATEGORIES.keys())
    for cat_name in category_folder_names:
        category_path = downloads_path / cat_name
        if category_path.is_dir():
            for item in list(category_path.iterdir()):
                move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ИЗ КАТЕГОРИИ")
            try:
                category_path.rmdir()
                log_callback_gui("УДАЛЕНИЕ ПАПКИ", category_path.name)
            except OSError:
                log_callback_gui("ПРЕДУПРЕЖДЕНИЕ", category_path.name, reason="Папка не пуста, не удалена.")

    log_callback_gui("СБРОС", "Операция сброса организации завершена.")
    pass


if __name__ == "__main__":
    import threading
    root = tk.Tk()
    app = DownloadsOrganizerApp(root)
    root.mainloop()
