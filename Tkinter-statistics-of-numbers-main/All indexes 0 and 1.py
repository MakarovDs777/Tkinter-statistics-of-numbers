import os
import tkinter as tk
from tkinter import filedialog

# Если хотите индексы, начинающиеся с 1, поставьте True
ONE_BASED = False

# Создаём скрытое окно Tkinter
root = tk.Tk()
root.withdraw()

# Открываем диалог для выбора файла
file_path = filedialog.askopenfilename(
    title="Выберите файл с последовательностью 0 и 1",
    filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
)

if not file_path:
    print("Файл не выбран.")
    exit()

# Чтение содержимого файла и фильтрация — оставляем только '0' и '1'
with open(file_path, 'r', encoding='utf-8') as f:
    raw = f.read()
data = ''.join(ch for ch in raw if ch in '01')

# Смещение индекса (0- или 1-начало)
offset = 1 if ONE_BASED else 0

# Списки индексов
indices_0 = [i + offset for i, ch in enumerate(data) if ch == '0']
indices_1 = [i + offset for i, ch in enumerate(data) if ch == '1']

# Подготовка строк с индексами (через пробел)
indices_0_str = ' '.join(map(str, indices_0))
indices_1_str = ' '.join(map(str, indices_1))

# Сохранение результатов на рабочем столе
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_path = os.path.join(desktop_path, "indices.txt")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"индексы 0: {indices_0_str}\n")
    f.write(f"индексы 1: {indices_1_str}\n")

print(f"Результаты сохранены в: {output_path}")
