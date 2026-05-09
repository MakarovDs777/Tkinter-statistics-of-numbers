import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading

def setup_clipboard_bindings(widget):
    def gen(event_name):
        return lambda e: (widget.event_generate(event_name), "break")

    widget.bind("<Control-c>", gen("<<Copy>>"))
    widget.bind("<Control-v>", gen("<<Paste>>"))
    widget.bind("<Control-x>", gen("<<Cut>>"))
    widget.bind("<Control-a>", lambda e: (widget.tag_add("sel", "1.0", "end"), "break"))

    widget.bind("<Command-c>", gen("<<Copy>>"))
    widget.bind("<Command-v>", gen("<<Paste>>"))
    widget.bind("<Command-x>", gen("<<Cut>>"))
    widget.bind("<Command-a>", lambda e: (widget.tag_add("sel", "1.0", "end"), "break"))

    widget.bind("<Button-1>", lambda e: widget.focus_set())

    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
    menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
    menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))
    menu.add_separator()
    menu.add_command(label="Выделить всё", command=lambda: widget.tag_add("sel", "1.0", "end"))

    def show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)
    widget.bind("<Control-Button-1>", show_menu)

def get_desktop_path():
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Рабочий стол"),
        os.path.join(home, "Рабочий_стол")
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return home

def load_numbers_file():
    path = filedialog.askopenfilename(
        filetypes=[("Text files", "*.txt;*.csv"), ("All files", "*.*")]
    )
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
        return

    numbers_text.delete("1.0", tk.END)
    numbers_text.insert("1.0", content)

def choose_input_folder():
    path = filedialog.askdirectory(title="Выберите папку с файлами file_X.txt")
    if path:
        input_folder_var.set(path)

def choose_output_folder():
    path = filedialog.askdirectory(title="Выберите папку для сохранения результатов")
    if path:
        output_folder_var.set(path)

def generate_local():
    """Локальный режим: обрабатывает текст из поля ввода."""
    raw = numbers_text.get("1.0", tk.END).strip()
    if not raw:
        messagebox.showerror("Ошибка", "Поле с числами пусто.")
        return

    try:
        min_val = int(min_var.get().strip())
        max_val = int(max_var.get().strip())
    except ValueError:
        messagebox.showerror("Ошибка", "Минимальное и максимальное значения должны быть целыми числами.")
        return

    if min_val > max_val:
        messagebox.showerror("Ошибка", "Минимальное значение не может быть больше максимального.")
        return

    if max_val - min_val > 1000:
        if not messagebox.askyesno("Подтверждение", f"Будет создано {max_val - min_val + 1} файлов. Продолжить?"):
            return

    tokens = re.split(r'(\d+\.?\d*)', raw)

    # Проверяем, есть ли целые числа
    has_numbers = False
    for token in tokens:
        try:
            val = float(token)
            if val == int(val):
                has_numbers = True
                break
        except ValueError:
            pass

    if not has_numbers:
        messagebox.showerror("Ошибка", "В тексте не найдено ни одного целого числа.")
        return

    desktop = get_desktop_path()
    output_dir = os.path.join(desktop, "processed_numbers_batch")
    os.makedirs(output_dir, exist_ok=True)

    def worker():
        total = max_val - min_val + 1
        for idx, keep_value in enumerate(range(min_val, max_val + 1)):
            result_parts = []
            for token in tokens:
                try:
                    val = float(token)
                    if val == int(val):
                        val = int(val)
                    else:
                        result_parts.append(token)
                        continue
                except ValueError:
                    result_parts.append(token)
                    continue

                if val == keep_value:
                    result_parts.append("1")
                else:
                    result_parts.append("0")

            result_text = "".join(result_parts)
            filename = f"file_{keep_value}.txt"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(result_text)

            progress_var.set(f"Локальный: {idx + 1} / {total}")
            progress_bar["value"] = (idx + 1) / total * 100
            root.update_idletasks()

        root.after(0, lambda: (
            messagebox.showinfo("Готово", f"Все файлы созданы в папке:\n{output_dir}"),
            progress_var.set("Готово ✓ (локальный)")
        ))

    progress_var.set("Начинаю локальную генерацию...")
    progress_bar["value"] = 0
    threading.Thread(target=worker, daemon=True).start()

def generate_global():
    """Глобальный режим: читает файлы из папки, собирает все индексы 1."""
    input_folder = input_folder_var.get()
    output_folder = output_folder_var.get()

    if not input_folder:
        messagebox.showerror("Ошибка", "Выберите папку с исходными файлами.")
        return
    if not output_folder:
        messagebox.showerror("Ошибка", "Выберите папку для сохранения результатов.")
        return
    if not os.path.isdir(input_folder):
        messagebox.showerror("Ошибка", "Указанная папка не существует.")
        return

    # Собираем все файлы file_X.txt
    file_pattern = re.compile(r'file_(\d+)\.txt$')
    input_files = []
    for fname in os.listdir(input_folder):
        m = file_pattern.match(fname)
        if m:
            filepath = os.path.join(input_folder, fname)
            if os.path.isfile(filepath):
                input_files.append((int(m.group(1)), filepath))

    if not input_files:
        messagebox.showerror("Ошибка", "В выбранной папке не найдено файлов вида file_X.txt")
        return

    # Сортируем по номеру
    input_files.sort(key=lambda x: x[0])

    def worker():
        total_files = len(input_files)
        # Для каждого файла собираем позиции, где стоит "1"
        # Структура: {номер_файла: [позиции_единиц]}
        all_positions = {}

        for idx, (file_num, filepath) in enumerate(input_files):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось прочитать {filepath}:\n{e}"))
                return

            # Находим все позиции символа "1"
            positions = [i for i, ch in enumerate(content) if ch == "1"]
            all_positions[file_num] = positions

            progress_var.set(f"Глобальный: читаю файл {idx + 1} / {total_files}")
            progress_bar["value"] = (idx + 1) / total_files * 100
            root.update_idletasks()

        # Теперь создаём выходную структуру:
        # Для каждой уникальной позиции (индекса) создаём файл,
        # где перечислены номера файлов, у которых в этой позиции стоит "1"
        
        # Собираем все уникальные позиции
        all_indexes = set()
        for positions in all_positions.values():
            all_indexes.update(positions)
        
        all_indexes = sorted(all_indexes)

        if not all_indexes:
            root.after(0, lambda: (
                messagebox.showinfo("Результат", "Ни в одном файле не найдено единиц."),
                progress_var.set("Готово (нет единиц)")
            ))
            return

        os.makedirs(output_folder, exist_ok=True)

        total_indexes = len(all_indexes)
        for idx, pos in enumerate(all_indexes):
            # Собираем номера файлов, у которых в позиции pos стоит "1"
            files_with_one = [file_num for file_num, positions in all_positions.items() if pos in positions]
            
            # Создаём файл index_{pos}.txt со списком номеров файлов
            filename = f"index_{pos}.txt"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                for file_num in files_with_one:
                    f.write(f"{file_num}\n")

            progress_var.set(f"Глобальный: создаю файлы {idx + 1} / {total_indexes}")
            progress_bar["value"] = (idx + 1) / total_indexes * 100
            root.update_idletasks()

        root.after(0, lambda: (
            messagebox.showinfo("Готово", 
                f"Обработано файлов: {total_files}\n"
                f"Найдено индексов с единицами: {total_indexes}\n"
                f"Результаты сохранены в:\n{output_folder}"),
            progress_var.set("Готово ✓ (глобальный)")
        ))

    progress_var.set("Начинаю глобальную обработку...")
    progress_bar["value"] = 0
    threading.Thread(target=worker, daemon=True).start()

def clear_numbers():
    numbers_text.delete("1.0", tk.END)

# ============================================================
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ============================================================

root = tk.Tk()
root.title("Пакетный обработчик — Локальный / Глобальный режим")
root.geometry("900+50+50")
root.minsize(860, 750)

# Создаём вкладки с помощью Notebook
notebook = ttk.Notebook(root)
notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# ==========================================
# ВКЛАДКА 1: ЛОКАЛЬНЫЙ РЕЖИМ
# ==========================================
local_tab = ttk.Frame(notebook)
notebook.add(local_tab, text="🔧 Локальный режим")

# Заголовок
header_local = tk.Label(local_tab, text="=== ЛОКАЛЬНЫЙ РЕЖИМ: обработка текста ===", font=("Arial", 14, "bold"))
header_local.pack(pady=(12, 8))

# Панель управления
control_frame = tk.Frame(local_tab)
control_frame.pack(fill=tk.X, padx=10, pady=6)

load_btn = tk.Button(control_frame, text="Загрузить файл с числами", command=load_numbers_file)
load_btn.pack(side=tk.LEFT, padx=(0, 10))

# Диапазон значений
range_frame = tk.Frame(control_frame)
range_frame.pack(side=tk.LEFT, padx=(0, 10))

tk.Label(range_frame, text="От:").pack(side=tk.LEFT)
min_var = tk.StringVar(value="0")
min_entry = tk.Entry(range_frame, textvariable=min_var, width=6)
min_entry.pack(side=tk.LEFT, padx=(2, 8))

tk.Label(range_frame, text="До:").pack(side=tk.LEFT)
max_var = tk.StringVar(value="255")
max_entry = tk.Entry(range_frame, textvariable=max_var, width=6)
max_entry.pack(side=tk.LEFT, padx=2)

generate_local_btn = tk.Button(control_frame, text="🔄 Сгенерировать (локально)", command=generate_local, bg="#4CAF50", fg="white")
generate_local_btn.pack(side=tk.LEFT, padx=(0, 10))

clear_btn = tk.Button(control_frame, text="Очистить поле", command=clear_numbers)
clear_btn.pack(side=tk.LEFT)

# Текстовое поле для чисел
text_frame = tk.Frame(local_tab)
text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

numbers_text = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 11))
n_yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=numbers_text.yview)
n_xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=numbers_text.xview)
numbers_text.configure(yscrollcommand=n_yscroll.set, xscrollcommand=n_xscroll.set)
n_yscroll.pack(side=tk.RIGHT, fill=tk.Y)
n_xscroll.pack(side=tk.BOTTOM, fill=tk.X)
numbers_text.pack(fill=tk.BOTH, expand=True)

setup_clipboard_bindings(numbers_text)

# Подсказка для локального режима
hint_local = tk.Label(
    local_tab,
    text="📌 Как это работает (локальный режим):\n"
         "1. Вставьте или загрузите текст с числами.\n"
         "2. Укажите диапазон значений (по умолчанию 0–255).\n"
         "3. Нажмите «Сгенерировать».\n"
         "4. Для каждого числа из диапазона будет создан отдельный файл:\n"
         "   - file_0.txt — число 0 заменено на 1, все остальные на 0\n"
         "   - file_1.txt — число 1 заменено на 1, все остальные на 0\n"
         "   - ... и так далее до file_255.txt\n"
         "5. Все файлы сохраняются в папку 'processed_numbers_batch' на рабочем столе.",
    anchor="w", justify=tk.LEFT, wraplength=800,
    font=("Arial", 10), fg="#555"
)
hint_local.pack(fill=tk.X, padx=10, pady=(4, 12))

# ==========================================
# ВКЛАДКА 2: ГЛОБАЛЬНЫЙ РЕЖИМ
# ==========================================
global_tab = ttk.Frame(notebook)
notebook.add(global_tab, text="🌐 Глобальный режим")

# Заголовок
header_global = tk.Label(global_tab, text="=== ГЛОБАЛЬНЫЙ РЕЖИМ: обработка папки с файлами ===", font=("Arial", 14, "bold"))
header_global.pack(pady=(12, 8))

# Панель выбора папок
folder_frame = tk.Frame(global_tab)
folder_frame.pack(fill=tk.X, padx=20, pady=10)

# Входная папка
tk.Label(folder_frame, text="📂 Папка с файлами file_X.txt:", font=("Arial", 11)).pack(anchor=tk.W)
input_folder_var = tk.StringVar(value="")
input_folder_entry = tk.Entry(folder_frame, textvariable=input_folder_var, width=70, state="readonly")
input_folder_entry.pack(fill=tk.X, pady=(2, 8))
input_folder_btn = tk.Button(folder_frame, text="Выбрать папку...", command=choose_input_folder)
input_folder_btn.pack(anchor=tk.W)

# Выходная папка
tk.Label(folder_frame, text="📁 Папка для результатов:", font=("Arial", 11)).pack(anchor=tk.W, pady=(10, 0))
output_folder_var = tk.StringVar(value="")
output_folder_entry = tk.Entry(folder_frame, textvariable=output_folder_var, width=70, state="readonly")
output_folder_entry.pack(fill=tk.X, pady=(2, 8))
output_folder_btn = tk.Button(folder_frame, text="Выбрать папку...", command=choose_output_folder)
output_folder_btn.pack(anchor=tk.W)

# Кнопка запуска
generate_global_btn = tk.Button(global_tab, text="🚀 Запустить глобальную обработку", command=generate_global, 
                                bg="#2196F3", fg="white", font=("Arial", 12, "bold"))
generate_global_btn.pack(pady=20)

# Подсказка для глобального режима
hint_global = tk.Label(
    global_tab,
    text="📌 Как это работает (глобальный режим):\n"
         "1. Выберите папку, в которой лежат файлы file_0.txt, file_1.txt, ..., file_255.txt\n"
         "   (эти файлы создаются локальным режимом).\n"
         "2. Выберите папку, куда сохранять результаты.\n"
         "3. Нажмите «Запустить глобальную обработку».\n"
         "4. Программа прочитает все файлы и для каждого индекса (позиции символа)\n"
         "   создаст файл index_{позиция}.txt, в котором перечислены номера файлов,\n"
         "   у которых в этой позиции стоит '1'.\n"
         "5. Пример: если в file_5.txt на позиции 12 стоит '1',\n"
         "   то в index_12.txt будет строка с числом 5.",
    anchor="w", justify=tk.LEFT, wraplength=800,
    font=("Arial", 10), fg="#555"
)
hint_global.pack(fill=tk.X, padx=20, pady=(10, 20))

# ==========================================
# ПРОГРЕСС-БАР (общий для обеих вкладок)
# ==========================================
progress_frame = tk.Frame(root)
progress_frame.pack(fill=tk.X, padx=10, pady=(4, 8))

progress_var = tk.StringVar(value="Ожидание...")
progress_label = tk.Label(progress_frame, textvariable=progress_var, font=("Arial", 10))
progress_label.pack(anchor=tk.W)

progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=800, mode="determinate")
progress_bar.pack(fill=tk.X, pady=(2, 0))

root.mainloop()
