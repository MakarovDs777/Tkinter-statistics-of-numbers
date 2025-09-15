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

# Подсчёт
count_0 = data.count('0')
count_1 = data.count('1')

# Список индексов единиц
if ONE_BASED:
    indices = [i + 1 for i, ch in enumerate(data) if ch == '1']
else:
    indices = [i for i, ch in enumerate(data) if ch == '1']

# Сохранение результатов на рабочем столе
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_path = os.path.join(desktop_path, "counts_and_indices.txt")

with open(output_path, 'w', encoding='utf-8') as f:
    f.write(f"Количество 0: {count_0}\n")
    f.write(f"Количество 1: {count_1}\n")
    f.write("\n")
    # Записываем массив индексов в формате [n, n, ...]
    f.write(str(indices) + "\n")

print(f"Результаты сохранены в: {output_path}")
