import win32com.client

def cp(*coords):
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
        coords
    )

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

# СИЛОС #6 bounds з structured_schema.json
min_x, max_x = 297.31, 338.33
min_y, max_y = 44.45, 82.63

print(f'Пошук силосу #6 в bounds X=[{min_x}, {max_x}], Y=[{min_y}, {max_y}]')

# Знаходимо ВСІ об'єкти в цих bounds
silo_6_objects = []

for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        # Тільки лінії
        if 'Line' in obj.EntityName:
            start = obj.StartPoint

            # Перевіряємо чи в bounds
            if (min_x <= start[0] <= max_x) and (min_y <= start[1] <= max_y):
                # Перевіряємо колір (синій = 5)
                if hasattr(obj, 'Color') and obj.Color == 5:
                    silo_6_objects.append(obj)
    except:
        pass

    if i % 10000 == 0:
        print(f'  {i}/{ms.Count}')

print(f'Знайдено {len(silo_6_objects)} обєктів силосу #6')

# Копіюємо зі зміщенням
offset = 50  # мм
copied = []

for obj in silo_6_objects:
    try:
        start = obj.StartPoint
        end = obj.EndPoint

        new_line = ms.AddLine(
            cp(start[0] + offset, start[1], 0),
            cp(end[0] + offset, end[1], 0)
        )
        new_line.Color = 5
        copied.append(new_line)
    except:
        pass

print(f'Скопійовано {len(copied)} ліній')

doc.Regen(1)
acad.ZoomExtents()
print('ГОТОВО!')
