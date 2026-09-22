# Grain Elevator Plugin - Інструкція по використанню

## ✅ ПЛАГІН УСПІШНО СТВОРЕНИЙ!

Файл: `d:\autocad project\Plant3D_Plugin\bin\Release\net8.0\GrainElevatorPlugin.dll`

---

## КРОК 1: Завантажити плагін в AutoCAD

1. В AutoCAD натисни **F2** (відкрити консоль)
2. Введи команду:
   ```
   NETLOAD
   ```
3. В діалозі вибери файл:
   ```
   d:\autocad project\Plant3D_Plugin\bin\Release\net8.0\GrainElevatorPlugin.dll
   ```
4. Натисни **Open**

Якщо все ок, побачиш повідомлення:
```
*** Grain Elevator Plugin Loaded ***
Available commands:
  CREATESILO - Create parametric silo
  CREATEELEVATOR - Create bucket elevator
  GENERATESCHEME - Generate complete scheme from JSON
  SCALESILOS - Scale selected silos
```

---

## КРОК 2: Використати команди

### Команда 1: CREATESILO

Створює ОДИН параметричний силос.

```
Command: CREATESILO
Enter silo diameter (mm): 22000
Enter silo height (mm): 24000
Specify insertion point: [клікни в кресленні]
Enter equipment tag (e.g., MSVU-220.13): MSVU-220.13.A3
```

Результат: Намалюється силос з синіми лініями + текст з позначкою + обчислений об'єм!

---

### Команда 2: GENERATESCHEME

Генерує ВСІХ силосів з JSON файлу автоматично!

```
Command: GENERATESCHEME
Enter path to scheme JSON file: d:\autocad project\scheme_config.json
```

Результат: Створить 7 силосів згідно конфігурації!

---

### Команда 3: SCALESILOS

Масштабує вибрані об'єкти (використовує AutoCAD TransformBy - СПРАВЖНЄ масштабування!)

```
Command: SCALESILOS
Select silos to scale: [вибери об'єкти]
Enter scale factor (e.g., 1.25 for 25% increase): 1.25
Specify base point for scaling: [клікни центр]
```

Результат: Об'єкти збільшені на 25% з ПРАВИЛЬНИМ масштабуванням геометрії!

---

## КРОК 3: Редагувати JSON конфігурацію

Файл: `d:\autocad project\scheme_config.json`

```json
{
  "Name": "Grain Elevator System - 7 Silos",
  "Silos": [
    {
      "X": 0,
      "Y": 0,
      "Diameter": 22000,
      "Height": 24000,
      "Tag": "MSVU-220.13.A3"
    },
    ...
  ]
}
```

**Зміни параметри:**
- `X`, `Y` - позиція в мм
- `Diameter` - діаметр в мм
- `Height` - висота в мм
- `Tag` - позначка обладнання

Потім запусти `GENERATESCHEME` і схема згенерується автоматично!

---

## ПЕРЕВАГИ цього плагіна:

✅ **Параметричність** - змінюєш JSON → автоматично генеруються силоси
✅ **Масштабування працює** - використовує AutoCAD API TransformBy
✅ **Автоматичні обчислення** - об'єм силоса обчислюється автоматично
✅ **Extended Data** - параметри зберігаються в об'єктах
✅ **Розширюваність** - можна додати команди для elevator, conveyor, etc.

---

## Що далі?

1. **Додати CREATEELEVATOR** - аналогічно CREATESILO
2. **Додати CREATECONVEYOR** - генерація конвеєрів між силосами
3. **Автоматичний BOM** - команда яка рахує всі силоси і генерує таблицю
4. **Автоматичні траси** - розумне з'єднання equipment

**Все це можна зробити в цьому ж плагіні!**

---

## Проблеми?

Якщо плагін не завантажується - перевір:
- .NET 8.0 Runtime встановлено
- AutoCAD 2026 (не 2025!)
- Шлях до DLL правильний
