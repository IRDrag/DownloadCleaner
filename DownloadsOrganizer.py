import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
import json
import os
import shutil
import time
import re
from datetime import datetime

CONFIG_FILENAME = "organizer_config.json"
LOG_FILENAME_APP_PREFIX = "Рекомендации_по_очистке_app"

# Эти настройки будут загружаться из config.json или использоваться по умолчанию
DEFAULT_SETTINGS = {
    "downloads_dir_name": "Downloads",
    "archive_dir_name": "Downloads_Archive",
    "days_older_to_archive": 7,
    "folders_to_ignore": ["Важные_Проекты_Не_Трогать"],
}

# Настройки, которые пока не вынесены в GUI и config.json для простоты (можно будет добавить в будущем)

ARCHIVE_GENERAL_OLD_SUBDIR = "01_Общий_архив_старше_недели"
ARCHIVE_SPECIFIC_ARCHIVES_OLD_SUBDIR = "02_Архивы_программ_старше_недели"
ARCHIVE_JUNK_BASE_SUBDIR = "03_Потенциальный_мусор"
ARCHIVED_OLD_FOLDERS_SUBDIR = "04_Архив_Старых_Папок"

JUNK_SUBDIR_BY_EXTENSION = "Junk_По_Расширению"
JUNK_SUBDIR_BY_KEYWORD = "Junk_По_Ключевому_Слову"
JUNK_SUBDIR_WINDOWS_DUPLICATES = "Junk_Дубликаты_Windows"

JUNK_KEYWORDS = ["старая_версия", "old_version", "backup", "резервная_копия", "temp", "tmpfile"]
JUNK_EXTENSIONS = [".tmp", ".log", ".bak", ".temp", "._gstmp"]

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
        self.root.title("Органайзер Загрузок v5")
        self.root.geometry("700x650")

        self.settings = DEFAULT_SETTINGS.copy()
        # self.load_config() # MOVED THIS CALL DOWN

        self.recommendations_log_entries = [] # Для файлового лога
        self.file_log_path = None

        # --- Стили ---
        style = ttk.Style()
        style.configure("TButton", padding=5, font=('Arial', 10))
        style.configure("TLabel", padding=5, font=('Arial', 10))
        style.configure("TFrame", padding=10)
        style.configure("Header.TLabel", font=('Arial', 12, 'bold'))

        # --- Основной фрейм ---
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Фрейм настроек ---
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding=10)
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        # --- Настройка: Дни для архивации ---
        ttk.Label(settings_frame, text="Дней до архивации:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.days_var = tk.StringVar(value=str(self.settings.get("days_older_to_archive", 7))) # Initialize with default
        self.days_entry = ttk.Entry(settings_frame, textvariable=self.days_var, width=5)
        self.days_entry.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # --- Настройка: Папка Загрузок (пока не редактируется через GUI, но отображается) ---
        ttk.Label(settings_frame, text="Папка Загрузок:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.downloads_dir_label_var = tk.StringVar(value=str(Path.home() / self.settings.get("downloads_dir_name", "Downloads"))) # Initialize with default
        ttk.Label(settings_frame, textvariable=self.downloads_dir_label_var, relief="sunken", width=40).grid(row=1, column=1, columnspan=2, sticky=tk.EW, pady=2)

        # --- Настройка: Папки-исключения ---
        ttk.Label(settings_frame, text="Папки-исключения:").grid(row=2, column=0, sticky=tk.NW, pady=2)
        
        ignore_list_frame = ttk.Frame(settings_frame)
        ignore_list_frame.grid(row=2, column=1, columnspan=2, sticky=tk.NSEW, pady=2)
        settings_frame.grid_columnconfigure(1, weight=1)

        self.ignore_listbox = tk.Listbox(ignore_list_frame, height=4, exportselection=False)
        self.ignore_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_ignore = ttk.Scrollbar(ignore_list_frame, orient=tk.VERTICAL, command=self.ignore_listbox.yview)
        scrollbar_ignore.pack(side=tk.RIGHT, fill=tk.Y)
        self.ignore_listbox.config(yscrollcommand=scrollbar_ignore.set)

        # Data for ignore_listbox will be populated after load_config

        ignore_buttons_frame = ttk.Frame(settings_frame)
        ignore_buttons_frame.grid(row=3, column=1, columnspan=2, sticky=tk.EW)

        self.ignore_entry_var = tk.StringVar()
        self.ignore_entry = ttk.Entry(ignore_buttons_frame, textvariable=self.ignore_entry_var, width=30)
        self.ignore_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))

        self.add_ignore_button = ttk.Button(ignore_buttons_frame, text="Добавить", command=self.add_to_ignore_list)
        self.add_ignore_button.pack(side=tk.LEFT, padx=(0,5))
        self.remove_ignore_button = ttk.Button(ignore_buttons_frame, text="Удалить выбранное", command=self.remove_from_ignore_list)
        self.remove_ignore_button.pack(side=tk.LEFT)
        
        # --- Кнопка Сохранить настройки ---
        self.save_settings_button = ttk.Button(settings_frame, text="Сохранить настройки", command=self.save_ui_config)
        self.save_settings_button.grid(row=4, column=0, columnspan=3, pady=10)

        # --- Фрейм действий ---
        actions_frame = ttk.LabelFrame(main_frame, text="Действия", padding=10)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        self.run_button = ttk.Button(actions_frame, text="Запустить организацию", command=self.run_organization_thread)
        self.run_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        self.rollback_button = ttk.Button(actions_frame, text="Сбросить организацию", command=self.perform_rollback_thread)
        self.rollback_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        # --- Лог в GUI ---
        log_frame = ttk.LabelFrame(main_frame, text="Лог операций", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED) # self.log_text IS NOW DEFINED
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar_log = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar_log.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar_log.set)

        # NOW it's safe to call load_config and then log messages
        self.load_config() # MOVED HERE

        self.gui_log("Приложение Органайзер Загрузок запущено.")
        self.gui_log(f"Текущая папка загрузок (из настроек): {self.downloads_dir_label_var.get()}")


    def gui_log(self, message, to_file_too=True):
        """Выводит сообщение в лог GUI и опционально в файловый лог."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        full_message = f"[{timestamp}] {message}"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, full_message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks() # Обновляем GUI

        if to_file_too:
            self.recommendations_log_entries.append(full_message)

    def add_to_ignore_list(self):
        folder_name = self.ignore_entry_var.get().strip()
        if folder_name:
            if folder_name not in self.ignore_listbox.get(0, tk.END):
                self.ignore_listbox.insert(tk.END, folder_name)
                self.ignore_entry_var.set("")
                self.gui_log(f"Папка '{folder_name}' добавлена в список исключений (не забудьте сохранить).", to_file_too=False)
            else:
                messagebox.showwarning("Дубликат", f"Папка '{folder_name}' уже есть в списке.")
        else:
            messagebox.showwarning("Пустое имя", "Введите имя папки для добавления.")

    def remove_from_ignore_list(self):
        selected_indices = self.ignore_listbox.curselection()
        if selected_indices:
            folder_name = self.ignore_listbox.get(selected_indices[0])
            self.ignore_listbox.delete(selected_indices[0])
            self.gui_log(f"Папка '{folder_name}' удалена из списка исключений (не забудьте сохранить).", to_file_too=False)
        else:
            messagebox.showwarning("Ничего не выбрано", "Выберите папку в списке для удаления.")

    def load_config(self):
        try:
            if Path(CONFIG_FILENAME).exists():
                with open(CONFIG_FILENAME, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                self.gui_log(f"Настройки загружены из {CONFIG_FILENAME}", to_file_too=False)
            else:
                self.gui_log(f"Файл настроек {CONFIG_FILENAME} не найден, используются значения по умолчанию.", to_file_too=False)
        except Exception as e:
            self.gui_log(f"Ошибка загрузки настроек: {e}. Используются значения по умолчанию.", to_file_too=False)
            messagebox.showerror("Ошибка загрузки конфига", f"Не удалось загрузить настройки из {CONFIG_FILENAME}:\n{e}")
            self.settings = DEFAULT_SETTINGS.copy()
        
        if hasattr(self, 'days_var'):
            self.days_var.set(str(self.settings.get("days_older_to_archive", 7)))
            self.downloads_dir_label_var.set(str(Path.home() / self.settings.get("downloads_dir_name", "Downloads")))
        if hasattr(self, 'ignore_listbox'):
            self.ignore_listbox.delete(0, tk.END)
            for folder in self.settings.get("folders_to_ignore", []):
                self.ignore_listbox.insert(tk.END, folder)


    def save_ui_config(self):
        """Собирает настройки из UI и сохраняет их."""
        try:
            self.settings["days_older_to_archive"] = int(self.days_var.get())
            self.settings["folders_to_ignore"] = list(self.ignore_listbox.get(0, tk.END))
            self.settings["downloads_dir_name"] = self.settings.get("downloads_dir_name", DEFAULT_SETTINGS["downloads_dir_name"])
            self.settings["archive_dir_name"] = self.settings.get("archive_dir_name", DEFAULT_SETTINGS["archive_dir_name"])


            with open(CONFIG_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            self.gui_log(f"Настройки сохранены в {CONFIG_FILENAME}", to_file_too=False)
            messagebox.showinfo("Настройки", "Настройки успешно сохранены.")
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Количество дней должно быть целым числом.")
            self.gui_log("Ошибка сохранения: неверное значение для дней.", to_file_too=False)
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить настройки:\n{e}")
            self.gui_log(f"Ошибка сохранения настроек: {e}", to_file_too=False)

    def _prepare_for_operation(self, operation_name):
        self.recommendations_log_entries = [] 
        self.file_log_path = Path.home() / self.settings["downloads_dir_name"] / self.settings["archive_dir_name"] / f"{LOG_FILENAME_APP_PREFIX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        self.gui_log(f"--- {operation_name} ЗАПУЩЕН ---", to_file_too=False)
        self.recommendations_log_entries.append(f"--- Лог операций: {operation_name} от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
        self.recommendations_log_entries.append(f"Папка Загрузок: {Path.home() / self.settings['downloads_dir_name']}")
        self.recommendations_log_entries.append(f"Папка Архива (внутри Загрузок): {Path.home() / self.settings['downloads_dir_name'] / self.settings['archive_dir_name']}")
        if operation_name == "ОРГАНИЗАЦИЯ":
            self.recommendations_log_entries.append(f"Игнорируемые папки: {self.settings['folders_to_ignore']}")
            self.recommendations_log_entries.append(f"Элементы старше {self.settings['days_older_to_archive']} дней перемещались в архив.")
        self.recommendations_log_entries.append("----------------------------------------------------------------------")
        
        self.run_button.config(state=tk.DISABLED)
        self.rollback_button.config(state=tk.DISABLED)
        self.save_settings_button.config(state=tk.DISABLED)


    def _finalize_operation(self, operation_name):
        self.recommendations_log_entries.append("----------------------------------------------------------------------")
        self.recommendations_log_entries.append(f"--- {operation_name} ЗАВЕРШЕН ---")
        
        log_save_dir = self.file_log_path.parent
        if operation_name == "СБРОС ОРГАНИЗАЦИИ" and not log_save_dir.exists():
            log_save_dir = Path.home() / self.settings["downloads_dir_name"] # Сохраняем в корень Загрузок
            self.file_log_path = log_save_dir / self.file_log_path.name 
            self.gui_log(f"Папка архива удалена, лог будет сохранен в: {log_save_dir}", to_file_too=False)

        ensure_dir_exists_logic(log_save_dir, self.gui_log_action) # Используем логику для создания папки

        try:
            with open(self.file_log_path, "w", encoding="utf-8") as f:
                for entry in self.recommendations_log_entries:
                    f.write(entry + "\n")
            self.gui_log(f"Файловый лог сохранен: \"{self.file_log_path}\"", to_file_too=False)
        except Exception as e:
            self.gui_log(f"Ошибка записи файлового лога \"{self.file_log_path}\": {e}", to_file_too=False)

        self.gui_log(f"--- {operation_name} ЗАВЕРШЕН ---", to_file_too=False) # Сообщение в GUI
        messagebox.showinfo(operation_name, f"{operation_name} завершен(а). Подробности в логе.")
        
        self.run_button.config(state=tk.NORMAL)
        self.rollback_button.config(state=tk.NORMAL)
        self.save_settings_button.config(state=tk.NORMAL)

    def run_organization_thread(self):

        if not messagebox.askyesno("Подтверждение", "Запустить организацию папки Загрузок? Это может занять некоторое время."):
            return
        self._prepare_for_operation("ОРГАНИЗАЦИЯ")
        try:
            run_organization_logic(self.settings, self.gui_log_action)
        except Exception as e:
            self.gui_log_action("КРИТИЧЕСКАЯ ОШИБКА при организации", "", f"Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла критическая ошибка во время организации:\n{e}")
        self._finalize_operation("ОРГАНИЗАЦИЯ")

    def perform_rollback_thread(self):
        if not messagebox.askyesno("Подтверждение СБРОСА", 
                                   "Вы уверены, что хотите сбросить всю организацию?\n"
                                   "Все файлы из папок категорий и архива будут возвращены в корень Загрузок.\n"
                                   "Созданные скриптом папки будут удалены.\n"
                                   "ЭТО ДЕЙСТВИЕ НЕОБРАТИМО (кроме повторной организации)."):
            return
        self._prepare_for_operation("СБРОС ОРГАНИЗАЦИИ")
        try:
            perform_rollback_logic(self.settings, self.gui_log_action)
        except Exception as e:
            self.gui_log_action("КРИТИЧЕСКАЯ ОШИБКА при сбросе", "", f"Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Произошла критическая ошибка во время сброса:\n{e}")
        self._finalize_operation("СБРОС ОРГАНИЗАЦИИ")
    
    def gui_log_action(self, action_type, item_path_obj_or_name, destination_parent_path_obj=None, reason=""):
        """Обертка для log_action, чтобы использовать в GUI."""
        item_name = item_path_obj_or_name.name if isinstance(item_path_obj_or_name, Path) else str(item_path_obj_or_name)
        
        log_item_name = item_name
        if "_ИЗ_КАТЕГОРИИ" in action_type and isinstance(item_path_obj_or_name, Path) and item_path_obj_or_name.parent.name in FILE_TYPE_CATEGORIES.keys():
             log_item_name = f"{item_path_obj_or_name.parent.name}/{item_name}"

        message = f"{action_type}: \"{log_item_name}\""
        
        if destination_parent_path_obj:
            try:
                home_path = Path.home()
                rel_dest_parent = destination_parent_path_obj.relative_to(home_path)
                message += f" -> {home_path.name}/{rel_dest_parent}" # e.g., User/Downloads/Archive_Folder
            except ValueError:
                message += f" -> {destination_parent_path_obj}"
                
        if reason:
            message += f" (Причина: {reason})"
        
        self.gui_log(message) # Это отправляет в GUI лог и файловый лог


# --- Функции логики (адаптированы из organize_downloads_v4.py) ---

def ensure_dir_exists_logic(dir_path, log_callback):
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_callback("ОШИБКА СОЗДАНИЯ ПАПКИ", dir_path, reason=f"Не удалось создать папку: {e}")

def is_file_older_than_logic(file_path, days):
    try:
        file_mod_time_ts = file_path.stat().st_mtime
        cutoff_time_ts = time.time() - (days * 24 * 60 * 60)
        return file_mod_time_ts < cutoff_time_ts
    except FileNotFoundError:
        return False

def is_folder_content_old_logic(folder_to_check_path, days, ignored_folder_names_list, log_callback):
    cutoff_time_ts = time.time() - (days * 24 * 60 * 60)
    has_any_content_not_ignored = False

    # Проверяем, не является ли сама папка игнорируемой (хотя это должно быть отфильтровано раньше)
    if folder_to_check_path.name in ignored_folder_names_list:
        log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path, reason="Папка в списке игнорирования, считается 'не старой'")
        return False

    for item in folder_to_check_path.rglob("*"):
        part_of_ignored = False
        for ignored_name in ignored_folder_names_list:
            # Создаем путь к потенциальной игнорируемой папке внутри folder_to_check_path
            # или если folder_to_check_path сама является дочерней для игнорируемой (что маловероятно здесь)
            if ignored_name in item.parts: # Если имя игнорируемой папки есть в пути к элементу
                # Более точная проверка: item.is_relative_to(folder_to_check_path / ignored_name) не сработает так просто
                # Проверяем, начинается ли относительный путь item от folder_to_check_path с ignored_name
                try:
                    relative_to_check = item.relative_to(folder_to_check_path)
                    if relative_to_check.parts[0] == ignored_name:
                        part_of_ignored = True
                        break
                except ValueError: # item не находится внутри folder_to_check_path (не должно случиться с rglob)
                    pass 
        
        if part_of_ignored:
            try:
                ignored_root_path = None
                for i_part_idx, i_part_name in enumerate(item.parts):
                    if i_part_name in ignored_folder_names_list:
                        # Собрать путь до этой папки
                        ignored_root_path = Path(*item.parts[:i_part_idx+1])
                        break
                if ignored_root_path and ignored_root_path.exists() and ignored_root_path.is_dir():
                     if ignored_root_path.stat().st_mtime >= cutoff_time_ts:
                        log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path, reason=f"Содержит свежую игнорируемую подпапку: {ignored_root_path.name}")
                        return False # Свежая игнорируемая подпапка делает родителя "не старым"
            except FileNotFoundError:
                pass # Если игнорируемая папка исчезла, это не делает родителя свежим
            continue # Пропускаем сам элемент из игнорируемой подпапки


        has_any_content_not_ignored = True
        try:
            if item.stat().st_mtime >= cutoff_time_ts:
                log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path, reason=f"Найден свежий элемент: {item.name}")
                return False 
        except FileNotFoundError:
            continue

    if not has_any_content_not_ignored:
        try:
            is_old = folder_to_check_path.stat().st_mtime < cutoff_time_ts
            log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path, reason=f"Папка пуста или содержит только старые игнорируемые. Сама папка {'старая' if is_old else 'свежая'}.")
            return is_old
        except FileNotFoundError:
            log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path.name, reason="Папка не найдена (возможно, удалена), считаем 'старой'.")
            return True 
    
    log_callback("ИНФО (ПРОВЕРКА СТАРОСТИ)", folder_to_check_path, reason="Все содержимое старое (или папка пуста и стара).")
    return True

def move_item_safely_logic(source_path, target_dir_path, log_callback, action_type="Перемещение", reason=""):
    if not source_path.exists():
        log_callback("ПРЕДУПРЕЖДЕНИЕ", source_path.name, reason="Исходный элемент не найден для перемещения.")
        return
    
    ensure_dir_exists_logic(target_dir_path, log_callback)
    original_item_name = source_path.name
    target_path = target_dir_path / original_item_name
    counter = 1
    base_name = source_path.stem if source_path.is_file() else original_item_name
    suffix = source_path.suffix if source_path.is_file() else ""

    while target_path.exists():
        new_name_candidate = f"{base_name}_{counter}{suffix}" if source_path.is_file() else f"{base_name}_{counter}"
        if source_path.is_dir() and Path(target_dir_path / new_name_candidate).is_file() and not new_name_candidate.endswith(suffix):
             # Если папка с таким именем (_counter) это файл, ищем дальше
             pass
        target_path = target_dir_path / new_name_candidate
        counter += 1
        if counter > 200: # Увеличил лимит для надежности
            log_callback("ОШИБКА ПЕРЕМЕЩЕНИЯ", original_item_name, target_dir_path, f"Слишком много элементов с похожим именем '{base_name}'.")
            return
    try:
        shutil.move(str(source_path), str(target_path))
        log_callback(action_type, source_path, target_dir_path, reason) # Передаем source_path для корректного лога имени
    except Exception as e:
        log_callback("ОШИБКА ПЕРЕМЕЩЕНИЯ", original_item_name, target_dir_path, f"{e}")

def is_windows_duplicate_name_logic(filename):
    pattern = re.compile(r"(.+)\s\(\d+\)(\.[^.]+)?$")
    return bool(pattern.match(filename))

def get_file_category_name_logic(file_path):
    extension = file_path.suffix.lower()
    if not extension: return "10_Другое"
    for cat_name, exts_list in FILE_TYPE_CATEGORIES.items():
        if extension in exts_list: return cat_name
    return "10_Другое"

def run_organization_logic(current_settings, log_callback_gui):
    """Основная логика организации файлов."""
    downloads_dir_name = current_settings["downloads_dir_name"]
    archive_dir_name = current_settings["archive_dir_name"]
    days_older_to_archive = current_settings["days_older_to_archive"]
    folders_to_ignore = current_settings["folders_to_ignore"]

    home_dir = Path.home()
    downloads_path = home_dir / downloads_dir_name
    
    if not downloads_path.is_dir():
        log_callback_gui("КРИТИЧЕСКАЯ ОШИБКА", downloads_path.name, reason="Папка Загрузок не найдена.")
        return

    archive_base_path = downloads_path / archive_dir_name # Архив ВНУТРИ Загрузок
    ensure_dir_exists_logic(archive_base_path, log_callback_gui)
    
    archive_general_old_path = archive_base_path / ARCHIVE_GENERAL_OLD_SUBDIR
    archive_specific_archives_old_path = archive_base_path / ARCHIVE_SPECIFIC_ARCHIVES_OLD_SUBDIR
    archive_old_folders_path = archive_base_path / ARCHIVED_OLD_FOLDERS_SUBDIR
    archive_junk_main_path = archive_base_path / ARCHIVE_JUNK_BASE_SUBDIR
    
    ensure_dir_exists_logic(archive_general_old_path, log_callback_gui)
    ensure_dir_exists_logic(archive_specific_archives_old_path, log_callback_gui)
    ensure_dir_exists_logic(archive_old_folders_path, log_callback_gui)
    ensure_dir_exists_logic(archive_junk_main_path, log_callback_gui)

    junk_by_ext_path = archive_junk_main_path / JUNK_SUBDIR_BY_EXTENSION
    junk_by_keyword_path = archive_junk_main_path / JUNK_SUBDIR_BY_KEYWORD
    junk_win_dup_path = archive_junk_main_path / JUNK_SUBDIR_WINDOWS_DUPLICATES
    ensure_dir_exists_logic(junk_by_ext_path, log_callback_gui)
    ensure_dir_exists_logic(junk_by_keyword_path, log_callback_gui)
    ensure_dir_exists_logic(junk_win_dup_path, log_callback_gui)

    category_folder_names = list(FILE_TYPE_CATEGORIES.keys())
    for cat_name in category_folder_names:
        ensure_dir_exists_logic(downloads_path / cat_name, log_callback_gui)
    
    folders_to_skip_in_main_loop = folders_to_ignore + [archive_dir_name] + category_folder_names
    log_file_name_for_run = Path(LOG_FILENAME_APP_PREFIX).stem + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".txt"


    log_callback_gui("ЭТАП 1", "Обработка элементов на верхнем уровне Загрузок")
    for item_path in list(downloads_path.iterdir()):
        if item_path.name.startswith(LOG_FILENAME_APP_PREFIX) or item_path.name in folders_to_skip_in_main_loop:
            if item_path.name in folders_to_ignore:
                 log_callback_gui("ПРОПУСК (ИГНОР)", item_path, reason="Папка в списке FOLDERS_TO_IGNORE")
            continue

        if item_path.is_file():
            filename = item_path.name
            file_ext_lower = item_path.suffix.lower()
            is_moved = False

            junk_reason = ""; target_junk_folder = None
            if file_ext_lower in JUNK_EXTENSIONS:
                junk_reason = f"расширение ({file_ext_lower})"; target_junk_folder = junk_by_ext_path
            elif any(keyword.lower() in filename.lower() for keyword in JUNK_KEYWORDS):
                keyword_found = next((k for k in JUNK_KEYWORDS if k.lower() in filename.lower()), "не_найдено")
                junk_reason = f"ключевое слово ('{keyword_found}')"; target_junk_folder = junk_by_keyword_path
            elif is_windows_duplicate_name_logic(filename):
                junk_reason = "похож на дубликат Windows"; target_junk_folder = junk_win_dup_path

            if target_junk_folder:
                move_item_safely_logic(item_path, target_junk_folder, log_callback_gui, "В АРХИВ (МУСОР)", junk_reason)
                is_moved = True
            
            if is_moved: continue

            if is_file_older_than_logic(item_path, days_older_to_archive):
                dest_path = archive_specific_archives_old_path if file_ext_lower in PROGRAM_ARCHIVE_EXTENSIONS else archive_general_old_path
                reason_str = f"старше {days_older_to_archive} дней"
                action_str = "В АРХИВ (СТАРЫЙ АРХИВ ПРОГРАММ)" if file_ext_lower in PROGRAM_ARCHIVE_EXTENSIONS else "В АРХИВ (СТАРЫЙ ФАЙЛ)"
                move_item_safely_logic(item_path, dest_path, log_callback_gui, action_str, reason_str)
                is_moved = True

            if is_moved: continue
                
            category_name = get_file_category_name_logic(item_path)
            move_item_safely_logic(item_path, downloads_path / category_name, log_callback_gui, "СОРТИРОВКА", f"категория '{category_name}'")

        elif item_path.is_dir():
            if is_folder_content_old_logic(item_path, days_older_to_archive, folders_to_ignore, log_callback_gui):
                move_item_safely_logic(item_path, archive_old_folders_path, log_callback_gui, "В АРХИВ (СТАРАЯ ПАПКА)", f"все содержимое старше {days_older_to_archive} дней")
            else:
                log_callback_gui("ИНФО", item_path, reason=f"Папка активна, оставлена без изменений.")
    
    log_callback_gui("ЭТАП 2", "Проверка на старость файлов внутри папок категорий")
    for category_name in category_folder_names:
        category_path = downloads_path / category_name
        if not category_path.is_dir(): continue

        for item_in_category_path in list(category_path.iterdir()): # list() для безопасного изменения во время итерации
            if item_in_category_path.is_file():
                if is_file_older_than_logic(item_in_category_path, days_older_to_archive):
                    file_ext_lower = item_in_category_path.suffix.lower()
                    dest_path = archive_specific_archives_old_path if file_ext_lower in PROGRAM_ARCHIVE_EXTENSIONS else archive_general_old_path
                    reason_str = f"старше {days_older_to_archive} дней"
                    action_str = "В АРХИВ (СТАРЫЙ АРХИВ ПРОГРАММ_ИЗ_КАТЕГОРИИ)" if file_ext_lower in PROGRAM_ARCHIVE_EXTENSIONS else "В АРХИВ (СТАРЫЙ ФАЙЛ_ИЗ_КАТЕГОРИИ)"
                    move_item_safely_logic(item_in_category_path, dest_path, log_callback_gui, action_str, reason_str)


def perform_rollback_logic(current_settings, log_callback_gui):
    """Логика полного сброса организации."""
    downloads_dir_name = current_settings["downloads_dir_name"]
    archive_dir_name = current_settings["archive_dir_name"]
    # folders_to_ignore не используется напрямую в rollback, т.к. мы удаляем только известные папки скрипта

    home_dir = Path.home()
    downloads_path = home_dir / downloads_dir_name
    archive_base_path = downloads_path / archive_dir_name
    
    log_callback_gui("СБРОС", "Начало операции сброса организации.")

    # 1. Обработка папки архива
    if archive_base_path.is_dir():
        log_callback_gui("СБРОС", archive_base_path.name, reason="Обработка папки архива.")
        
        archived_old_folders_path_obj = archive_base_path / ARCHIVED_OLD_FOLDERS_SUBDIR
        if archived_old_folders_path_obj.is_dir():
            log_callback_gui("СБРОС", archived_old_folders_path_obj.name, reason="Возврат старых папок пользователя.")
            for item in list(archived_old_folders_path_obj.iterdir()): # list() для безопасной итерации
                move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ПАПКИ ИЗ АРХИВА")
            try:
                shutil.rmtree(archived_old_folders_path_obj) # Удаляем папку, если она стала пустой
                log_callback_gui("УДАЛЕНИЕ ПАПКИ", archived_old_folders_path_obj.name, reason="Папка архива старых папок удалена.")
            except OSError as e: # OSError если не пустая или нет прав
                 log_callback_gui("ОШИБКА УДАЛЕНИЯ", archived_old_folders_path_obj.name, reason=f"Не удалось удалить папку: {e}")


        archive_subfolders_to_empty = [
            archive_base_path / ARCHIVE_GENERAL_OLD_SUBDIR,
            archive_base_path / ARCHIVE_SPECIFIC_ARCHIVES_OLD_SUBDIR,
            archive_base_path / ARCHIVE_JUNK_BASE_SUBDIR # Включая его подпапки
        ]
        
        for archive_subfolder_path in archive_subfolders_to_empty:
            if archive_subfolder_path.is_dir():
                log_callback_gui("СБРОС", archive_subfolder_path.name, reason="Возврат содержимого.")
                folders_to_process_in_archive = [archive_subfolder_path]
                processed_folders_for_deletion = set()

                while folders_to_process_in_archive:
                    current_folder = folders_to_process_in_archive.pop(0)
                    processed_folders_for_deletion.add(current_folder)
                    for item in list(current_folder.iterdir()): # list() для безопасной итерации
                        if item.is_file():
                            move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ФАЙЛА ИЗ АРХИВА")
                        elif item.is_dir():
                            # Если это папка внутри подпапки архива (например, Junk_По_Расширению),
                            # добавляем ее в очередь для обработки ее содержимого.
                            folders_to_process_in_archive.append(item) 
                
                for folder_to_delete in sorted(list(processed_folders_for_deletion), key=lambda p: len(p.parts), reverse=True):
                    try:
                        if folder_to_delete.exists() and not list(folder_to_delete.iterdir()): # Только если пустая
                             folder_to_delete.rmdir() # Удаляем, если стала пустой
                             log_callback_gui("УДАЛЕНИЕ ПАПKI", folder_to_delete.name, reason="Подпапка архива удалена.")
                        elif folder_to_delete.exists(): # Если не пустая после перемещения
                            shutil.rmtree(folder_to_delete) # Принудительное удаление, если что-то осталось
                            log_callback_gui("УДАЛЕНИЕ ПАПKI (ПРИНУДИТЕЛЬНО)", folder_to_delete.name, reason="Подпапка архива удалена (rmtree).")

                    except OSError as e:
                        log_callback_gui("ОШИБКА УДАЛЕНИЯ", folder_to_delete.name, reason=f"Не удалось удалить подпапку архива: {e}")
        
        try:
            if archive_base_path.exists() and not list(archive_base_path.iterdir()):
                archive_base_path.rmdir()
                log_callback_gui("УДАЛЕНИЕ ПАПКИ", archive_base_path.name, reason="Основная папка архива удалена.")
            elif archive_base_path.exists():
                 log_callback_gui("ПРЕДУПРЕЖДЕНИЕ", archive_base_path.name, reason="Основная папка архива не пуста после обработки, не удалена.")
        except OSError as e:
            log_callback_gui("ОШИБКА УДАЛЕНИЯ", archive_base_path.name, reason=f"Не удалось удалить основную папку архива: {e}")

    else:
        log_callback_gui("СБРОС", archive_dir_name, reason="Папка архива не найдена, пропускается.")

    # 2. Обработка папок категорий
    category_folder_names = list(FILE_TYPE_CATEGORIES.keys())
    for cat_name in category_folder_names:
        category_path = downloads_path / cat_name
        if category_path.is_dir():
            log_callback_gui("СБРОС", category_path.name, reason="Возврат содержимого папки категории.")
            for item in list(category_path.iterdir()): # list() для безопасной итерации
                move_item_safely_logic(item, downloads_path, log_callback_gui, "ВОЗВРАТ ИЗ КАТЕГОРИИ")
            try:
                if category_path.exists() and not list(category_path.iterdir()): # Только если пустая
                    category_path.rmdir()
                    log_callback_gui("УДАЛЕНИЕ ПАПКИ", category_path.name, reason="Папка категории удалена.")
                elif category_path.exists():
                    log_callback_gui("ПРЕДУПРЕЖДЕНИЕ", category_path.name, reason="Папка категории не пуста после обработки, не удалена.")
            except OSError as e:
                 log_callback_gui("ОШИБКА УДАЛЕНИЯ", category_path.name, reason=f"Не удалось удалить папку категории: {e}")

        else:
            log_callback_gui("СБРОС", cat_name, reason="Папка категории не найдена, пропускается.")
    
    log_callback_gui("СБРОС", "Операция сброса организации завершена.")


if __name__ == "__main__":
    root = tk.Tk()
    app = DownloadsOrganizerApp(root)
    root.mainloop()
