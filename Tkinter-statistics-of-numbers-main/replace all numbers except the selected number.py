import os
import math
import tempfile
import wave
import struct
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog, messagebox

# Попытка импортировать pydub — не критично
try:
    from pydub import AudioSegment
    _HAS_PYDUB = True
except Exception:
    _HAS_PYDUB = False

image_data = None
canvas_img_refs = []
current_width = None
current_height = None

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
    widget.bind("<Control-Button-1>", show_menu)  # для macOS

def load_image():
    global image_data, current_width, current_height
    path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All files", "*.*")])
    if not path:
        return
    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось открыть изображение: {e}")
        return

    image_data = np.array(img)
    current_height, current_width = image_data.shape[:2]
    width_var.set(str(current_width))

    win = tk.Toplevel(root)
    win.title(f"Изображение — {os.path.basename(path)}")
    canvas = tk.Canvas(win, width=img.width, height=img.height)
    canvas.pack()
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)
    canvas_img_refs.append(photo)

    fill_text_from_image(image_data)

def fill_text_from_image(arr):
    h, w = arr.shape[:2]
    # Предупреждение для очень больших изображений
    max_cells_warn = 500000
    total = h * w
    if total > max_cells_warn:
        if not messagebox.askyesno("Большое изображение", f"Изображение содержит {total} пикселей. Это создаст {total} строк в табло и может сильно замедлить интерфейс. Продолжить?"):
            return

    lines = []
    # Идём в порядке строк (row-major)
    for row in arr:
        for px in row:
            r, g, b = int(px[0]), int(px[1]), int(px[2])
            lines.append(f"{r} {g} {b}")
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    text_widget.insert("1.0", "\n".join(lines))

def parse_rgb_text(text):
    pixels = []
    for i, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if "," in line:
            parts = [p.strip() for p in line.split(",") if p.strip() != ""]
        else:
            parts = [p for p in line.split() if p != ""]
        if len(parts) != 3:
            raise ValueError(f"Строка {i}: ожидается 3 числа (R G B), найдено {len(parts)}: '{raw_line}'")
        try:
            r, g, b = [int(p) for p in parts]
        except:
            raise ValueError(f"Строка {i}: неверный формат чисел: '{raw_line}'")
        for v in (r, g, b):
            if v < 0 or v > 255:
                raise ValueError(f"Строка {i}: значение {v} вне диапазона 0-255")
        pixels.append([r, g, b])
    if not pixels:
        raise ValueError("Не найдено ни одного RGB-триплета.")
    return pixels

def open_image_from_text():
    global image_data, current_width, current_height
    txt = text_widget.get("1.0", tk.END)
    try:
        pixels = parse_rgb_text(txt)
    except ValueError as e:
        messagebox.showerror("Ошибка парсинга", str(e))
        return

    w_text = width_var.get().strip()
    if w_text:
        try:
            w = int(w_text)
            if w <= 0:
                raise ValueError()
        except:
            messagebox.showerror("Ошибка", "Поле ширины должно содержать положительное целое число.")
            return
    else:
        n = len(pixels)
        sq = int(np.sqrt(n))
        if sq * sq == n:
            w = sq
        else:
            messagebox.showinfo("Уточнение", "Ширина не указана и длина не является квадратом. Пожалуйста, укажите ширину.")
            return

    if len(pixels) % w != 0:
        messagebox.showerror("Ошибка", f"Количество пикселей ({len(pixels)}) не делится на указанную ширину ({w}).")
        return

    arr = np.array(pixels, dtype=np.uint8)
    h = arr.shape[0] // w
    arr = arr.reshape((h, w, 3))
    image_data = arr
    current_height, current_width = h, w
    width_var.set(str(w))

    img = Image.fromarray(arr)
    win = tk.Toplevel(root)
    win.title("Изображение из RGB")
    canvas = tk.Canvas(win, width=img.width, height=img.height)
    canvas.pack()
    photo = ImageTk.PhotoImage(img)
    canvas.create_image(0, 0, anchor=tk.NW, image=photo)
    canvas_img_refs.append(photo)

def clear_text():
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)

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
    # fallback
    return home

def image_to_audio(arr,
                   total_duration=60.0,
                   sample_rate=22050,
                   f_min=200.0,
                   f_max=6000.0,
                   max_width=300,
                   max_height=128):
    """
    Преобразует RGB-массив (H,W,3) в моно аудиосигнал numpy float32 в диапазоне [-1,1].
    - Общая длительность аудио = total_duration (сек).
    - Каждая колонка изображения занимает duration_per_column = total_duration / width.
    - Изображение может быть уменьшено для скорости.
    """
    if total_duration <= 0:
        raise ValueError("total_duration должен быть положительным числом.")

    # Приведём к RGB numpy
    if arr.dtype != np.uint8:
        arr = (arr * 255).astype(np.uint8)
    h, w = arr.shape[:2]

    # Downscale если слишком большое
    scale_w = min(1.0, max_width / max(1, w))
    scale_h = min(1.0, max_height / max(1, h))
    scale = min(scale_w, scale_h)
    if scale < 1.0:
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        img = Image.fromarray(arr).resize((new_w, new_h), Image.BILINEAR)
        arr = np.array(img)
        h, w = arr.shape[:2]

    # Конвертируем в яркость для простоты
    brightness = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) / 255.0

    # Вычисляем длительность сегмента на колонку
    duration_per_column = total_duration / max(1, w)
    # Минимальная длина кадра в сэмплах — 1
    frame_len = max(1, int(sample_rate * duration_per_column))
    total_len = frame_len * w
    out = np.zeros(total_len, dtype=np.float32)
    t_frame = np.linspace(0, frame_len / sample_rate, frame_len, endpoint=False)

    # Предварительный массив частот для каждой строки (строка 0 -> верх -> высокая частота)
    if h == 1:
        freqs = np.array([(f_min + f_max) / 2.0])
    else:
        freqs = f_min + (f_max - f_min) * (1.0 - np.arange(h) / (h - 1))

    for col in range(w):
        col_b = brightness[:, col]
        active_idx = np.where(col_b > 0.001)[0]
        if active_idx.size == 0:
            seg = np.zeros(frame_len, dtype=np.float32)
        else:
            seg = np.zeros(frame_len, dtype=np.float32)
            for r in active_idx:
                amp = float(col_b[r])
                if amp <= 0:
                    continue
                f = freqs[r]
                seg += amp * np.sin(2.0 * np.pi * f * t_frame)
            # Нормализация сегмента
            max_abs = np.max(np.abs(seg))
            if max_abs > 0:
                seg /= max_abs
            seg *= min(1.0, 0.9 * (np.mean(col_b) * h / 8.0 + 0.1))
        out[col * frame_len:(col + 1) * frame_len] = seg

    # Нормализация на [-1,1]
    maxv = np.max(np.abs(out))
    if maxv > 0:
        out = out / maxv * 0.95
    return out, sample_rate

def save_wav_from_array(samples, sr, path_wav):
    """Сохранение wav 16-bit моно."""
    int_samples = np.int16(samples * 32767)
    with wave.open(path_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16 bit
        wf.setframerate(sr)
        wf.writeframes(int_samples.tobytes())

def save_audio():
    """Берёт либо загруженное изображение, либо строит его из текста, генерирует звук и сохраняет mp3 на рабочем стол."""
    global image_data
    arr = None
    if image_data is not None:
        arr = image_data
    else:
        # Попробуем собрать изображение из текста
        txt = text_widget.get("1.0", tk.END)
        try:
            pixels = parse_rgb_text(txt)
        except ValueError as e:
            messagebox.showerror("Ошибка парсинга", str(e))
            return
        w_text = width_var.get().strip()
        if w_text:
            try:
                w = int(w_text)
                if w <= 0:
                    raise ValueError()
            except:
                messagebox.showerror("Ошибка", "Поле ширины должно содержать положительное целое число.")
                return
        else:
            n = len(pixels)
            sq = int(np.sqrt(n))
            if sq * sq == n:
                w = sq
            else:
                messagebox.showinfo("Уточнение", "Ширина не указана и длина не является квадратом. Пожалуйста, укажите ширину.")
                return
        if len(pixels) % w != 0:
            messagebox.showerror("Ошибка", f"Количество пикселей ({len(pixels)}) не делится на указанную ширину ({w}).")
            return
        arr = np.array(pixels, dtype=np.uint8)
        h = arr.shape[0] // w
        arr = arr.reshape((h, w, 3))

    # Получаем длительность из поля
    dur_text = duration_var.get().strip()
    if not dur_text:
        total_duration = 60.0
    else:
        try:
            total_duration = float(dur_text)
            if total_duration <= 0:
                raise ValueError()
        except:
            messagebox.showerror("Ошибка", "Поле 'Длительность' должно содержать положительное число (секунды).")
            return

    # Предупреждение при слишком долгом аудио
    if total_duration > 600:
        if not messagebox.askyesno("Длинное аудио", f"Вы задали длительность {total_duration} секунд (>600). Генерация и экспорт могут занять много времени. Продолжить?"):
            return

    # Генерируем аудио
    try:
        samples, sr = image_to_audio(arr, total_duration=total_duration)
    except Exception as e:
        messagebox.showerror("Ошибка генерации аудио", f"Ошибка при генерации звука: {e}")
        return

    desktop = get_desktop_path()
    base_name = "sonification"
    mp3_path = os.path.join(desktop, f"{base_name}.mp3")
    wav_temp = None
    try:
        # Сначала временный WAV
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
        os.close(tmp_fd)
        wav_temp = tmp_path
        save_wav_from_array(samples, sr, wav_temp)

        if _HAS_PYDUB:
            try:
                audio = AudioSegment.from_wav(wav_temp)
                audio.export(mp3_path, format="mp3")
                messagebox.showinfo("Готово", f"MP3 сохранен на рабочем столе: {mp3_path}")
            except Exception as e:
                # возможно ffmpeg не найден
                fallback = os.path.join(desktop, "sonification.wav")
                os.replace(wav_temp, fallback)
                wav_temp = None
                messagebox.showwarning("Внимание",
                                       f"Не удалось экспортировать MP3 через pydub/ffmpeg: {e}\n"
                                       f"Сохранён WAV: {fallback}")
        else:
            # Без pydub — сохраняем WAV и предупреждаем
            fallback = os.path.join(desktop, "sonification.wav")
            os.replace(wav_temp, fallback)
            wav_temp = None
            messagebox.showinfo("Сохранено", f"pydub не установлен или ffmpeg недоступен. WAV сохранён: {fallback}\n"
                                             f"Чтобы получить MP3, установите pydub и ffmpeg.")
    finally:
        if wav_temp and os.path.exists(wav_temp):
            os.remove(wav_temp)

# ============================================================
# НОВЫЙ ФУНКЦИОНАЛ: загрузка чисел, замена на 0/1, сохранение
# ============================================================

def load_numbers_file():
    """Загружает текстовый файл с числами в поле ввода."""
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

    # Вставляем содержимое в текстовое поле (но не в основное, а в новое)
    numbers_text.delete("1.0", tk.END)
    numbers_text.insert("1.0", content)

def process_and_save():
    """
    Берёт числа из поля numbers_text:
    - все числа заменяет на 0
    - единственное выбранное число (которое ввёл пользователь) заменяет на 1
    - сохраняет результат на рабочий стол
    """
    raw = numbers_text.get("1.0", tk.END).strip()
    if not raw:
        messagebox.showerror("Ошибка", "Поле с числами пусто.")
        return

    # Какое число оставить как 1
    keep_str = keep_var.get().strip()
    if not keep_str:
        messagebox.showerror("Ошибка", "Введите число, которое должно стать 1.")
        return

    try:
        keep_value = float(keep_str)
        # Проверяем, что это целое (если нужно)
        if keep_value != int(keep_value):
            raise ValueError
        keep_value = int(keep_value)
    except ValueError:
        messagebox.showerror("Ошибка", "Число должно быть целым.")
        return

    # Разбиваем на токены (с保留ением разделителей)
    import re
    # Находим все числа и не-числа
    tokens = re.split(r'(\d+\.?\d*)', raw)

    result_parts = []
    number_found = False
    for token in tokens:
        # Пробуем распарсить как число
        try:
            val = float(token)
            if val == int(val):
                val = int(val)
            else:
                # Если не целое — оставляем как есть? Или заменяем на 0?
                # По задаче — работаем с целыми числами
                result_parts.append(token)
                continue
        except ValueError:
            # Это не число — разделитель/текст
            result_parts.append(token)
            continue

        # Это число
        number_found = True
        if val == keep_value:
            result_parts.append("1")
        else:
            result_parts.append("0")

    if not number_found:
        messagebox.showerror("Ошибка", "В тексте не найдено ни одного числа.")
        return

    result_text = "".join(result_parts)

    # Сохраняем на рабочий стол
    desktop = get_desktop_path()
    output_path = os.path.join(desktop, "processed_numbers.txt")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result_text)
        messagebox.showinfo("Готово", f"Файл сохранён:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")

# ============================================================
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ============================================================

root = tk.Tk()
root.title("RGB редактор Tkinter — Sonification + Numbers")
root.geometry("980x900")

# ---- Верхняя панель (старая) ----
top_frame = tk.Frame(root)
top_frame.pack(fill=tk.X, padx=8, pady=6)

# Кнопка загрузки изображения (показывает и заполняет табло)
load_btn = tk.Button(top_frame, text="Загрузить изображение", command=load_image)
load_btn.pack(side=tk.LEFT, padx=(0, 6))

width_label = tk.Label(top_frame, text="Ширина (px):")
width_label.pack(side=tk.LEFT)
width_var = tk.StringVar()
width_entry = tk.Entry(top_frame, textvariable=width_var, width=8)
width_entry.pack(side=tk.LEFT, padx=(4, 12))

duration_label = tk.Label(top_frame, text="Длительность (сек.):")
duration_label.pack(side=tk.LEFT)
duration_var = tk.StringVar(value="60")  # по умолчанию 60 секунд
duration_entry = tk.Entry(top_frame, textvariable=duration_var, width=8)
duration_entry.pack(side=tk.LEFT, padx=(4, 12))

open_from_text_btn = tk.Button(top_frame, text="Открыть изображение из RGB", command=open_image_from_text)
open_from_text_btn.pack(side=tk.LEFT, padx=(0, 6))

save_audio_btn = tk.Button(top_frame, text="Сохранить аудио (MP3/WAV)", command=save_audio)
save_audio_btn.pack(side=tk.LEFT, padx=(6, 6))

clear_btn = tk.Button(top_frame, text="Очистить табло", command=clear_text)
clear_btn.pack(side=tk.LEFT)

# ---- Поле для RGB (старое) ----
text_frame = tk.Frame(root)
text_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

text_widget = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 11), height=10)
yscroll = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
xscroll = tk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=text_widget.xview)
text_widget.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
yscroll.pack(side=tk.RIGHT, fill=tk.Y)
xscroll.pack(side=tk.BOTTOM, fill=tk.X)
text_widget.pack(fill=tk.BOTH, expand=True)

setup_clipboard_bindings(text_widget)

hint = tk.Label(root, text="Формат: по одному триплету на строку: R G B (или R,G,B).\nЕсли поле 'Ширина' пустое, пытаемся подобрать квадрат.\nДлительность по умолчанию — 60 секунд. Нажмите 'Сохранить аудио' для получения MP3 (или WAV — если нет pydub/ffmpeg).",
                anchor="w", justify=tk.LEFT, wraplength=940)
hint.pack(fill=tk.X, padx=8, pady=(0, 8))

# ============================================================
# НОВАЯ СЕКЦИЯ: работа с числами
# ============================================================

separator = tk.Frame(root, height=2, bd=1, relief=tk.SUNKEN)
separator.pack(fill=tk.X, padx=8, pady=8)

numbers_label = tk.Label(root, text="=== РАБОТА С ЧИСЛАМИ ===", font=("Arial", 12, "bold"))
numbers_label.pack(pady=(0, 4))

# Панель управления числами
numbers_control = tk.Frame(root)
numbers_control.pack(fill=tk.X, padx=8, pady=4)

load_numbers_btn = tk.Button(numbers_control, text="Загрузить файл с числами", command=load_numbers_file)
load_numbers_btn.pack(side=tk.LEFT, padx=(0, 10))

keep_label = tk.Label(numbers_control, text="Оставить как 1 (число):")
keep_label.pack(side=tk.LEFT)
keep_var = tk.StringVar()
keep_entry = tk.Entry(numbers_control, textvariable=keep_var, width=10)
keep_entry.pack(side=tk.LEFT, padx=(4, 10))

process_btn = tk.Button(numbers_control, text="Обработать и сохранить", command=process_and_save)
process_btn.pack(side=tk.LEFT)

# Поле для ввода/редактирования чисел
numbers_frame = tk.Frame(root)
numbers_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

numbers_text = tk.Text(numbers_frame, wrap=tk.NONE, font=("Consolas", 11), height=8)
n_yscroll = tk.Scrollbar(numbers_frame, orient=tk.VERTICAL, command=numbers_text.yview)
n_xscroll = tk.Scrollbar(numbers_frame, orient=tk.HORIZONTAL, command=numbers_text.xview)
numbers_text.configure(yscrollcommand=n_yscroll.set, xscrollcommand=n_xscroll.set)
n_yscroll.pack(side=tk.RIGHT, fill=tk.Y)
n_xscroll.pack(side=tk.BOTTOM, fill=tk.X)
numbers_text.pack(fill=tk.BOTH, expand=True)

setup_clipboard_bindings(numbers_text)

numbers_hint = tk.Label(
    root,
    text="Вставьте или загрузите текст с числами. Все числа будут заменены на 0, а указанное число — на 1.\n"
         "Результат сохраняется на рабочий стол как 'processed_numbers.txt'.",
    anchor="w", justify=tk.LEFT, wraplength=940
)
numbers_hint.pack(fill=tk.X, padx=8, pady=(0, 8))

root.mainloop()
