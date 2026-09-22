import win32com.client

def cp(*coords):
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
        coords
    )

print('Копіювання ПОВНОГО силосу #6 -> #7')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument

# Отримати ModelSpace
try:
    ms = doc.ModelSpace
except:
    # Якщо не працює як властивість, спробувати метод
    try:
        ms = doc.get_ModelSpace()
    except:
        # Останній варіант - через PaperSpace/ModelSpace
        ms = doc.Application.ActiveDocument.ModelSpace

print(f'Загальна кількість об\'єктів: {ms.Count}')

# ПРАВИЛЬНІ bounds силосу #6 (з ezdxf аналізу)
# X: 0.76 -> 126.28, Y: 86.04 -> 126.00
# Розширю трохи щоб захопити всі деталі + норію зверху
silo_6_min_x = -10.0
silo_6_max_x = 136.0
silo_6_min_y = 76.0
silo_6_max_y = 500.0  # Збільшив щоб захопити норію

print(f'\nBounds пошуку силосу #6:')
print(f'  X: {silo_6_min_x} -> {silo_6_max_x}')
print(f'  Y: {silo_6_min_y} -> {silo_6_max_y}')

offset_x = 150.0  # Зміщення для силосу #7

# Пошук об'єктів
print(f'\nПошук об\'єктів в bounds...')
objects_to_copy = []

for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        # Перевірка чи об'єкт має координати
        in_bounds = False

        # Для ліній
        if hasattr(obj, 'StartPoint'):
            start = obj.StartPoint
            if (silo_6_min_x <= start[0] <= silo_6_max_x and
                silo_6_min_y <= start[1] <= silo_6_max_y):
                in_bounds = True

        if in_bounds:
            objects_to_copy.append(obj)

    except:
        pass

    # Прогрес
    if (i + 1) % 10000 == 0:
        print(f'  Оброблено {i+1}/{ms.Count}, знайдено: {len(objects_to_copy)}')

print(f'\nЗнайдено об\'єктів для копіювання: {len(objects_to_copy)}')

# Копіювання
print(f'\nКопіювання з offset X = {offset_x}...')
copied_count = 0

for obj in objects_to_copy:
    try:
        # Копіювати лінії
        if hasattr(obj, 'StartPoint') and hasattr(obj, 'EndPoint'):
            start = obj.StartPoint
            end = obj.EndPoint

            new_line = ms.AddLine(
                cp(start[0] + offset_x, start[1], 0),
                cp(end[0] + offset_x, end[1], 0)
            )

            # Копіювати властивості
            try:
                new_line.Color = obj.Color
            except:
                pass

            try:
                new_line.Layer = obj.Layer
            except:
                pass

            copied_count += 1

    except Exception as e:
        pass

print(f'\nСкопійовано: {copied_count} об\'єктів')

# Оновити креслення
try:
    doc.Regen(1)
except:
    pass

try:
    acad.ZoomExtents()
except:
    pass

print('\n' + '='*70)
print('ГОТОВО!')
print('='*70)
