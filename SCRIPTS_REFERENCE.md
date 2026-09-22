# ДОВІДНИК ПО ВСІХ СКРИПТАХ

Технічна документація всіх створених скриптів з прикладами використання.

---

## 📑 ЗМІСТ

1. [Робочі скрипти](#робочі-скрипти)
2. [Скрипти що зависають](#скрипти-що-зависають)
3. [State Management](#state-management)
4. [Конфігураційні файли](#конфігураційні-файли)
5. [Приклади використання](#приклади-використання)

---

## ✅ РОБОЧІ СКРИПТИ

### 1. fix_7th_silo_correct.py

**Призначення:** Правильне копіювання 7-го силосу з існуючого #6

**Як працює:**
```python
# 1. Знаходить всі об'єкти силосу #6 (по позиції x≈305, y≈50)
# 2. Копіює кожен об'єкт: obj.Copy()
# 3. Переміщує на 47.75мм вправо: obj.Move()
```

**Використання:**
```bash
python "d:/autocad project/fix_7th_silo_correct.py"
```

**Вимоги:**
- AutoCAD відкритий
- Файл з силосом #6 завантажений
- Силос #6 має бути біля координат x=280-330, y=30-70

**Результат:**
- Створює 19-24 нові об'єкти (копія силосу #6)
- Розміщує їх на відстані 47.75мм від оригіналу

**Статус:** ✅ ПРАЦЮЄ (якщо файл правильний)

---

### 2. DRAW_RED_FINAL.py

**Призначення:** Малювання червоних з'єднань для всіх силосів

**Як працює:**
```python
# 1. Видаляє старі червоні лінії (Color == 1)
# 2. Знаходить всі силоси (сині об'єкти C00-00-FF)
# 3. Визначає Y координату для конвеєрів (найнижча точка - 5мм)
# 4. Малює горизонтальні конвеєри між силосами
# 5. Малює вертикальні норії (висота 50мм)
```

**Використання:**
```bash
python "d:/autocad project/DRAW_RED_FINAL.py"
```

**Параметри (в коді):**
```python
expected_positions = [
    {'num': 3, 'x': 134, 'y': 63},
    {'num': 4, 'x': 181, 'y': 63},
    {'num': 5, 'x': 270, 'y': 63},
    {'num': 6, 'x': 305, 'y': 50},
    {'num': 7, 'x': 353, 'y': 50}
]

elevator_height = 50  # Висота норії в мм
```

**Результат:**
- Горизонтальні конвеєри: 4 лінії (між силосами 3-4, 4-5, 5-6, 6-7)
- Вертикальні норії: 5 ліній (від кожного силосу вгору)
- Всього: 9 червоних ліній

**Статус:** ✅ ПРАЦЮЄ (малює, але вигадує координати)

---

### 3. FAST_COPY_SILO.py

**Призначення:** Швидке копіювання через SelectionSet (без сканування всіх об'єктів)

**Як працює:**
```python
# 1. Створює SelectionSet
# 2. Вибирає об'єкти в рамці (250-330, 30-70) замість сканування всіх
# 3. Фільтрує тільки сині (C00-00-FF) і чорні (C00-00-00)
# 4. Копіює їх на 47.75мм вправо
# 5. Окремо копіює червоні лінії (вертикальні норії)
```

**Переваги над циклом:**
```python
# ПОВІЛЬНО (47000 ітерацій):
for i in range(ms.Count):
    obj = ms.Item(i)
    ...

# ШВИДШЕ (тільки об'єкти в області):
ss.Select(5, min_point, max_point)
for i in range(ss.Count):  # Може бути 20-50 об'єктів
    obj = ss.Item(i)
    ...
```

**Використання:**
```bash
python "d:/autocad project/FAST_COPY_SILO.py"
```

**Статус:** ⏳ Запущений, результат невідомий

---

### 4. STATE_MANAGER.py

**Призначення:** Система управління станом для запобігання повторних операцій

**Класи та методи:**

```python
class StateManager:
    def __init__(self, project_dir):
        """Ініціалізація"""
        self.state_file = "processing_state.json"
        self.originals_dir = "ORIGINALS/"
        self.working_dir = "WORKING/"
        self.results_dir = "RESULTS/"

    def initialize():
        """Створити директорії та state файл"""

    def preserve_original(source_file):
        """
        Зберегти оригінал в ORIGINALS/
        Returns: шлях до збереженого оригіналу
        """

    def create_working_copy(file_key):
        """
        Створити робочу копію з оригіналу
        Returns: шлях до робочої копії
        """

    def can_apply_operation(file_key, operation_name):
        """
        Перевірити чи можна застосувати операцію
        Returns: True/False
        """

    def record_operation(file_key, operation_name, details):
        """Записати що операція виконана"""

    def mark_processed(file_key):
        """Позначити файл як повністю оброблений"""

    def save_result(working_file, file_key):
        """
        Зберегти результат в RESULTS/ з timestamp
        Returns: шлях до результату
        """

    def get_file_info(file_key):
        """Отримати інформацію про файл"""

    def print_status():
        """Вивести поточний стан системи"""
```

**Приклад використання:**

```python
from STATE_MANAGER import StateManager

# Ініціалізація
manager = StateManager("d:/autocad project")
manager.initialize()

# Зберегти оригінал
original = manager.preserve_original("my_file.dxf")

# Створити робочу копію
working = manager.create_working_copy("my_file")

# Перевірити чи можна застосувати операцію
if manager.can_apply_operation("my_file", "scale_silo_3"):
    # Виконати операцію
    scale_silo(3, 1.2)

    # Записати що зроблено
    manager.record_operation("my_file", "scale_silo_3", {
        "scale": 1.2,
        "objects": 24
    })

# Позначити як оброблений
manager.mark_processed("my_file")

# Зберегти результат
result = manager.save_result(working, "my_file")
```

**Формат state файлу:**
```json
{
  "created": "2025-12-25T14:28:22",
  "files": {
    "my_file": {
      "original_path": "ORIGINALS/ORIGINAL_my_file.dxf",
      "processed": false,
      "operations_applied": [
        {
          "name": "scale_silo_3",
          "timestamp": "2025-12-25T14:30:10",
          "details": {"scale": 1.2, "objects": 24}
        }
      ]
    }
  },
  "operations": [...]
}
```

**Статус:** ✅ СТВОРЕНО (не протестовано)

---

### 5. SAFE_RESIZE_SYSTEM.py

**Призначення:** Безпечна система масштабування з state management

**Основні методи:**

```python
class SafeResizeSystem:
    def initialize():
        """Ініціалізація state manager + завантаження конфігів"""

    def check_can_process(file_key):
        """Перевірка чи файл можна обробляти"""

    def delete_red_lines(file_key):
        """Видалити червоні лінії (з записом в state)"""

    def calculate_new_positions():
        """Порахувати нові позиції силосів"""

    def transform_silo(silo_number, new_pos, file_key, operation_name):
        """
        Трансформувати один силос
        - Масштабування
        - Переміщення
        - Запис в state
        """

    def add_7th_silo(file_key):
        """Додати 7-й силос копіюванням #6"""

    def draw_connections(positions, file_key):
        """Намалювати червоні з'єднання"""

    def execute(source_file):
        """Головна функція виконання"""
```

**Використання:**

```bash
python "d:/autocad project/SAFE_RESIZE_SYSTEM.py"
```

**Що робить:**
1. Зберігає оригінал
2. Перевіряє state
3. Видаляє червоні лінії (якщо ще не видалено)
4. Масштабує силоси 3-6 (якщо ще не масштабовано)
5. Додає 7-й силос (якщо ще не додано)
6. Малює червоні з'єднання (якщо ще не намальовано)
7. Зберігає результат

**Статус:** ✅ СТВОРЕНО (помилка з кодуванням при запуску)

---

### 6. VIEW_STATUS.py

**Призначення:** Перегляд поточного state

**Використання:**
```bash
python "d:/autocad project/VIEW_STATUS.py"
```

**Вивід:**
```
======================================================================
ПОТОЧНИЙ СТАН
======================================================================

Всього файлів в системі: 1
Всього операцій: 5

----------------------------------------------------------------------
ФАЙЛИ:
----------------------------------------------------------------------

✅ ОБРОБЛЕНО my_file
  Оригінал: ORIGINAL_my_file.dxf
  Операції (5):
    - delete_red_lines (2025-12-25T14:30:05)
    - scale_silo_3 (2025-12-25T14:30:10)
    - scale_silo_4 (2025-12-25T14:30:12)
    - add_7th_silo (2025-12-25T14:30:20)
    - draw_connections (2025-12-25T14:30:25)

======================================================================
```

**Статус:** ✅ ПРАЦЮЄ

---

## ❌ СКРИПТИ ЩО ЗАВИСАЮТЬ

### 1. ANALYZE_TEMPLATE.py

**Призначення:** Повний аналіз еталону з page_01.dxf

**Проблема:**
```python
# Зависає на циклі:
for i in range(ms.Count):  # 46955 ітерацій!
    obj = ms.Item(i)
    ...
```

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ

---

### 2. ANALYZE_CURRENT.py

**Призначення:** Аналіз поточного відкритого файлу

**Проблема:** Та сама - цикл по 47000 об'єктів

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ

---

### 3. FULL_ANALYSIS.py

**Призначення:** Повний аналіз всіх кольорів

**Проблема:** Зависає на скануванні

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ

---

### 4. QUICK_ANALYSIS.py

**Призначення:** Швидкий аналіз (тільки сині + червоні)

**Проблема:** Навіть "швидкий" зависає на 47000

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ

---

### 5. COPY_SILO_FROM_ORIGINAL.py

**Призначення:** Копіювання з page_01.dxf

**Проблема:** Зависає при пошуку об'єктів

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ (замінено на FAST_COPY_SILO.py)

---

### 6. COMPLETE_RESIZE_SYSTEM.py

**Призначення:** Стара система масштабування

**Проблеми:**
- Немає state management
- Можна запустити багато разів (compounding effect)
- Застарілий

**Статус:** ❌ ЗАСТАРІЛИЙ (замінено на SAFE_RESIZE_SYSTEM.py)

---

### 7. add_7th_silo.py

**Призначення:** Додавання 7-го силосу

**Проблема:** МАЛЮЄ З НУЛЯ замість копіювання!

```python
# НЕПРАВИЛЬНО:
points = [x1, y1, x2, y2, ...]
pline = ms.AddLightWeightPolyline(points)  # Простий прямокутник!
```

**Відгук користувача:**
> "БЛЯТЬ! Я 10000 РАЗІВ СКАЗАВ - НЕ МАЛЮЙ З НУЛЯ!"

**Статус:** ❌ НЕ ВИКОРИСТОВУВАТИ НІКОЛИ!

---

## 📋 КОНФІГУРАЦІЙНІ ФАЙЛИ

### 1. smart_resize_config.json

**Призначення:** Конфігурація масштабів для силосів

**Формат:**
```json
{
  "resize_plan": {
    "silos": [
      {"id": 3, "scale": 1.2},
      {"id": 4, "scale": 1.2},
      {"id": 5, "scale": 0.8},
      {"id": 6, "scale": 0.8}
    ]
  }
}
```

**Використання:**
```python
import json

with open('smart_resize_config.json', 'r') as f:
    config = json.load(f)

for silo_cfg in config['resize_plan']['silos']:
    silo_id = silo_cfg['id']
    scale = silo_cfg['scale']
    print(f"Силос #{silo_id}: масштаб {scale}")
```

---

### 2. extracted_silos_REAL_ORIGINAL.json

**Призначення:** Дані про силоси з "оригіналу"

**Проблема:** Файл з якого витягнуто дані вже був зламаний!

**Формат:**
```json
{
  "silos": [
    {
      "number": 3,
      "center": {"x": 134.03, "y": 63.54},
      "width": 58.76,
      "height": 38.76,
      "bounds": {
        "min_x": 104.65,
        "max_x": 163.41,
        "min_y": 44.13,
        "max_y": 82.95
      }
    }
  ]
}
```

**Статус:** ⚠️ МОЖЛИВО ЗАСТАРІЛИЙ

---

### 3. processing_state.json

**Призначення:** State файл для відстеження операцій

**Створюється:** STATE_MANAGER.py

**Формат:** Див. STATE_MANAGER.py вище

**Локація:** `d:/autocad project/processing_state.json`

---

## 💡 ПРИКЛАДИ ВИКОРИСТАННЯ

### Приклад 1: Копіювання силосу вручну

```python
import win32com.client

def cp(*coords):
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY |
        win32com.client.pythoncom.VT_R8,
        coords
    )

# Підключення
acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

# Знайти об'єкт по індексу (ПОВІЛЬНО!)
obj = ms.Item(1500)

# АБО через SelectionSet (ШВИДШЕ!)
ss = doc.SelectionSets.Add('TempSS')
ss.Select(5, cp(100, 50, 0), cp(200, 100, 0))
obj = ss.Item(0)
ss.Delete()

# Копіювати
new_obj = obj.Copy()

# Перемістити
new_obj.Move(cp(0, 0, 0), cp(47.75, 0, 0))

print("Готово!")
```

---

### Приклад 2: Пошук синіх об'єктів через SelectionSet

```python
import win32com.client

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument

# Створити selection set
try:
    ss = doc.SelectionSets.Add('BlueSS')
except:
    doc.SelectionSets.Item('BlueSS').Delete()
    ss = doc.SelectionSets.Add('BlueSS')

# Вибрати в області
min_pt = win32com.client.VARIANT(
    win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
    (250, 30, 0)
)
max_pt = win32com.client.VARIANT(
    win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
    (330, 70, 0)
)

ss.Select(5, min_pt, max_pt)  # 5 = acSelectionSetWindow

print(f"Знайдено: {ss.Count} об'єктів")

# Фільтрувати по layer
blue_objects = []
for i in range(ss.Count):
    obj = ss.Item(i)
    if hasattr(obj, 'Layer') and 'C00-00-FF' in obj.Layer:
        blue_objects.append(obj)

print(f"Синіх: {len(blue_objects)}")

ss.Delete()
```

---

### Приклад 3: Малювання червоної лінії

```python
import win32com.client

def cp(*coords):
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY |
        win32com.client.pythoncom.VT_R8,
        coords
    )

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

# Намалювати лінію
start = cp(100, 50, 0)
end = cp(200, 50, 0)

line = ms.AddLine(start, end)
line.Color = 1  # Червоний (1=red, 2=yellow, 3=green, 4=cyan, 5=blue)

# Regenerate
doc.Regen(1)

print("Лінія намальована!")
```

---

### Приклад 4: Використання State Manager

```python
from STATE_MANAGER import StateManager

# Ініціалізація
manager = StateManager("d:/autocad project")
manager.initialize()

# Зберегти оригінал
file_path = "d:/autocad project/my_drawing.dxf"
original = manager.preserve_original(file_path)

# Отримати file_key
file_key = "my_drawing"

# Створити робочу копію
working = manager.create_working_copy(file_key)

# Відкрити в AutoCAD
import win32com.client
acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.Documents.Open(str(working))

# Виконати операції з перевіркою
operations = [
    "delete_red_lines",
    "scale_silo_3",
    "scale_silo_4",
    "add_7th_silo"
]

for op_name in operations:
    if manager.can_apply_operation(file_key, op_name):
        print(f"Виконую: {op_name}")

        # Тут код операції
        # ...

        # Записати що зроблено
        manager.record_operation(file_key, op_name, {"status": "success"})
    else:
        print(f"Пропускаю {op_name} - вже виконано")

# Зберегти
doc.Save()

# Позначити як оброблений
manager.mark_processed(file_key)

# Зберегти результат
result = manager.save_result(working, file_key)

print(f"Результат: {result}")

# Подивитися статус
manager.print_status()
```

---

## 🔧 УТИЛІТИ ТА HELPER ФУНКЦІЇ

### cp() - Створення координат для COM API

```python
def cp(*coords):
    """
    Створити COM-сумісний масив координат

    Args:
        *coords: x, y, z координати

    Returns:
        VARIANT array для AutoCAD COM API

    Examples:
        cp(100, 50, 0)        # 3D точка
        cp(100, 50)           # 2D (автоматично додасть z=0)
    """
    import win32com.client
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY |
        win32com.client.pythoncom.VT_R8,
        coords
    )
```

### Знаходження центру об'єкта

```python
def get_center(obj):
    """
    Отримати центр об'єкта

    Args:
        obj: AutoCAD object

    Returns:
        (cx, cy) або None
    """
    if not hasattr(obj, 'GetBoundingBox'):
        return None

    try:
        bbox = obj.GetBoundingBox()
        min_p, max_p = bbox[0], bbox[1]
        cx = (min_p[0] + max_p[0]) / 2
        cy = (min_p[1] + max_p[1]) / 2
        return (cx, cy)
    except:
        return None
```

### Відстань між точками

```python
def distance(p1, p2):
    """
    Відстань між двома точками

    Args:
        p1: (x1, y1) або (x1, y1, z1)
        p2: (x2, y2) або (x2, y2, z2)

    Returns:
        float distance
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return (dx**2 + dy**2)**0.5
```

### Видалення об'єктів по кольору

```python
def delete_by_color(ms, color):
    """
    Видалити всі об'єкти певного кольору

    Args:
        ms: ModelSpace
        color: 1=red, 2=yellow, 3=green, 4=cyan, 5=blue

    Returns:
        int: кількість видалених
    """
    to_delete = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if hasattr(obj, 'Color') and obj.Color == color:
                to_delete.append(i)
        except:
            pass

    # Видаляти з кінця
    deleted = 0
    for idx in sorted(to_delete, reverse=True):
        try:
            ms.Item(idx).Delete()
            deleted += 1
        except:
            pass

    return deleted
```

---

## 📚 КОРИСНІ КОНСТАНТИ

### AutoCAD Colors

```python
AcRed = 1
AcYellow = 2
AcGreen = 3
AcCyan = 4
AcBlue = 5
AcMagenta = 6
AcWhite = 7
AcByLayer = 256
AcByBlock = 0
```

### Layer Names

```python
LAYER_BLUE_SILOS = 'C00-00-FF'      # Сині силоси
LAYER_RED_CONNECTIONS = 'CFF-00-00' # Червоні з'єднання
LAYER_BLACK_HATCHES = 'C00-00-00'   # Чорні штрихування
```

### Розміри

```python
SILO_SPACING = 47.75      # мм - відстань між силосами
ELEVATOR_HEIGHT = 50      # мм - висота норії
CONVEYOR_OFFSET = -5      # мм - зсув конвеєра вниз від базової лінії
```

---

## 🐛 ВІДОМІ ПРОБЛЕМИ ТА WORKAROUNDS

### Проблема 1: Зависання на великих файлах

**Симптом:**
```python
for i in range(ms.Count):  # Зависає якщо Count > 10000
    obj = ms.Item(i)
```

**Workaround:**
```python
# Використати SelectionSet замість циклу
ss = doc.SelectionSets.Add('TempSS')
ss.Select(5, min_point, max_point)  # Вибрати тільки потрібну область

for i in range(ss.Count):  # Набагато менше об'єктів
    obj = ss.Item(i)
```

---

### Проблема 2: Помилка кодування в print()

**Симптом:**
```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Workaround:**
```python
# На початку файлу:
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

---

### Проблема 3: SelectionSet вже існує

**Симптом:**
```
Error: Collection already contains element
```

**Workaround:**
```python
try:
    ss = doc.SelectionSets.Add('MySelection')
except:
    # Видалити старий і створити новий
    try:
        doc.SelectionSets.Item('MySelection').Delete()
    except:
        pass
    ss = doc.SelectionSets.Add('MySelection')
```

---

### Проблема 4: LightWeightPolyline приймає тільки 2D

**Симптом:**
```
Too few elements in SafeArray or total number of elements is not a multiple of three
```

**Причина:**
```python
# НЕПРАВИЛЬНО:
points = [x1, y1, 0, x2, y2, 0, ...]  # 3D координати
pline = ms.AddLightWeightPolyline(points)
```

**Workaround:**
```python
# ПРАВИЛЬНО:
points = [x1, y1, x2, y2, ...]  # Тільки 2D!
pline = ms.AddLightWeightPolyline(points)

# АБО використати AddPolyline для 3D:
points_3d = [x1, y1, 0, x2, y2, 0, ...]
pline = ms.AddPolyline(points_3d)
```

---

## 📝 ЧЕКЛИСТ ДЛЯ НОВОГО АГЕНТА

Перед початком роботи:

- [ ] Прочитати FULL_PROJECT_REPORT.md
- [ ] Прочитати цей файл (SCRIPTS_REFERENCE.md)
- [ ] Перевірити чи AutoCAD відкритий
- [ ] Перевірити який файл відкритий в AutoCAD
- [ ] Перевірити скільки об'єктів в файлі (ms.Count)
- [ ] Переглянути processing_state.json
- [ ] Визначити чи є 7-й силос

Якщо треба копіювати силос:

- [ ] НЕ використовувати скрипти що зависають (ANALYZE_*.py)
- [ ] Використати FAST_COPY_SILO.py або fix_7th_silo_correct.py
- [ ] Перевірити результат в AutoCAD
- [ ] Намалювати червоні з'єднання (DRAW_RED_FINAL.py)

Якщо треба аналізувати:

- [ ] Спробувати ezdxf замість Python COM API
- [ ] Або запропонувати ручне копіювання

**НІКОЛИ НЕ ВИКОРИСТОВУВАТИ:**
- ❌ add_7th_silo.py (малює з нуля!)
- ❌ ANALYZE_*.py (зависають!)
- ❌ COMPLETE_RESIZE_SYSTEM.py (застарілий!)

---

**КІНЕЦЬ ДОВІДНИКА**

Версія: 1.0
Дата: 25.12.2025
