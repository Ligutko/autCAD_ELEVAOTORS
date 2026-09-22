# 🚀 ШВИДКИЙ СТАРТ - Revit MCP System

**Ваш статус:** Revit 2026 ✅ встановлений, pyRevit ❌ потрібно встановити

---

## ⚡ АВТОМАТИЧНЕ ВСТАНОВЛЕННЯ (РЕКОМЕНДОВАНО)

**Запустіть простий setup скрипт:**

```powershell
cd "D:\autocad project"
.\setup_revit_simple.ps1
```

Цей скрипт створить всі папки та встановить Python залежності.
**Після цього встановіть pyRevit вручну (див. нижче).**

---

## ⚡ ЩО РОБИТИ ЗАРАЗ (5 ХВИЛИН)

### Крок 1: Встановити pyRevit (5 хвилин)

**АВТОМАТИЧНО (рекомендую):**

1. Завантажити installer:
   - Перейти: https://github.com/pyrevitlabs/pyRevit/releases
   - Завантажити: `pyRevit_5.3.1.25308_signed.exe` ✅ (LATEST - Nov 2025)

2. Запустити інсталятор:
   - Подвійний клік на `pyRevit_4.8.x_signed.exe`
   - Обрати: **Revit 2026** ✅
   - Натиснути Install
   - Дочекатися завершення

3. Перевірити:
   - Відкрити Revit 2026
   - В інтерфейсі має з'явитися вкладка **"pyRevit"**
   - Якщо немає → перезапустити Revit

**АБО ВРУЧНУ (якщо автоматично не спрацювало):**

```powershell
# Завантажити pyRevit
Invoke-WebRequest -Uri "https://github.com/pyrevitlabs/pyRevit/releases/download/v4.8.16.24143/pyRevit_4.8.16.24143_signed.exe" -OutFile "$env:TEMP\pyrevit_installer.exe"

# Запустити
Start-Process "$env:TEMP\pyrevit_installer.exe" -Wait
```

---

### Крок 2: Налаштувати pyRevit Listener (2 хвилини)

**ПІСЛЯ встановлення pyRevit:**

1. Скопіювати listener скрипт:
```powershell
# Створити структуру
New-Item -Path "$env:APPDATA\pyRevit\Extensions\RevitMCP.extension\RevitMCP.tab\Listener.panel\StartListener.pushbutton" -ItemType Directory -Force

# Скопіювати скрипт
Copy-Item "D:\autocad project\revit-mcp\pyrevit_extension\revit_listener.py" "$env:APPDATA\pyRevit\Extensions\RevitMCP.extension\RevitMCP.tab\Listener.panel\StartListener.pushbutton\script.py"
```

2. Перезавантажити pyRevit:
   - У Revit: **pyRevit → Settings → Reload**

3. Має з'явитися кнопка **"Start Listener"**

---

### Крок 3: Тестування (1 хвилина)

1. **Створити тестовий проект:**
   - Revit → File → New → Project
   - Template: "Architectural Template"
   - Save As: `D:\autocad project\Test_Grain_Elevator.rvt`

2. **Запустити Listener:**
   - У Revit: натиснути кнопку **"Start Listener"**
   - В Output має з'явитися:
     ```
     ✅ Revit Listener Started
     Commands Queue: D:\autocad project\revit-mcp\commands_queue
     Waiting for commands...
     ```

3. **Тест з'єднання:**
   - Відкрити новий термінал (НЕ закривати Revit!)
   - Запустити:
     ```bash
     cd "D:\autocad project\revit-mcp"
     python test_mcp_connection.py
     ```
   - Має пройти 4 тести ✅

---

## 🎯 ЯКЩО ВСЕ ПРАЦЮЄ

**Ви побачите:**
```
✅ PASS  Ping Revit
✅ PASS  Get Project Info
✅ PASS  List Families
✅ PASS  List Sheets

🎉 ALL TESTS PASSED!
```

**Тоді готові до наступного кроку:**
- Створення Families (2-3 години)
- Автоматична побудова з JSON

---

## ❌ TROUBLESHOOTING

### Проблема: pyRevit вкладка не з'являється

**Рішення:**
1. Перезапустити Revit
2. Перевірити версію Revit (має бути 2026)
3. Запустити pyRevit CLI:
   ```powershell
   pyrevit attach 2026
   ```

---

### Проблема: "Revit listener NOT RESPONDING"

**Рішення:**
1. Перевірити чи Revit відкритий
2. Перевірити чи натиснута кнопка "Start Listener"
3. Перевірити шлях до черг:
   - Має бути: `D:\autocad project\revit-mcp\commands_queue`
   - Перевірити чи папка існує

---

### Проблема: Кнопка "Start Listener" не з'являється

**Рішення:**
1. Перевірити шлях до скрипта:
   ```
   %APPDATA%\pyRevit\Extensions\RevitMCP.extension\...\script.py
   ```
2. Переконатися що файл називається `script.py` (НЕ `revit_listener.py`)
3. Reload pyRevit

---

## 📞 НАСТУПНІ КРОКИ

### ЯКЩО все працює (тести пройшли):

**→ Перейти до створення Families**

Відкрити: [REVIT_COMPLETE_ROADMAP.md](REVIT_COMPLETE_ROADMAP.md) → Фаза 2

---

### ЯКЩО є проблеми:

**→ Скажіть мені і я допоможу!**

Напишіть які саме тести не пройшли або що не спрацювало.

---

## 🎓 КОРИСНІ КОМАНДИ

### Перевірити pyRevit:
```powershell
pyrevit --version
```

### Прикріпити pyRevit до Revit 2026:
```powershell
pyrevit attach 2026
```

### Відкрити папку pyRevit Extensions:
```powershell
explorer "%APPDATA%\pyRevit\Extensions"
```

### Перезавантажити pyRevit (в Revit):
- **pyRevit → Settings → Reload**

---

**Готові? Почніть з Кроку 1! ⬆️**

---

**Автор:** Claude Code
**Дата:** 2026-01-01
**Версія Revit:** 2026
