# 🏗️ Revit MCP Server - Професійна автоматизація Autodesk Revit

**Версія:** 0.1.0 (Прототип)
**Дата:** 2026-01-01
**Автор:** Claude Code (Sonnet 4.5)

---

## 📖 Що це?

**Revit MCP Server** — це Model Context Protocol сервер, який дозволяє **Claude Code керувати Autodesk Revit** через pyRevit.

### Можливості:

✅ **Імпорт DXF/CAD файлів** програмно (зберігає кольори та шари)
✅ **Аналіз геометрії** (LIDAR-підхід: кластеризація, розпізнавання об'єктів)
✅ **Завантаження Families** (.rfa файли) та розміщення екземплярів
✅ **Параметризація** — встановлення параметрів (діаметр, висота, тег)
✅ **Створення Sheets** (аркуші креслень) автоматично
✅ **Експорт в PDF** (один файл або окремі аркуші)
✅ **JSON конфігурація** — генерація проекту з `config_6_silos.json`

---

## 🏗️ Архітектура системи

```
┌─────────────────────┐         ┌──────────────────────┐         ┌────────────────┐
│   Claude Code       │ ◄─────► │  Revit MCP Server    │ ◄─────► │  Revit API     │
│   (Ви/Claude)       │  stdio  │  (Python)            │  Queue  │  (pyRevit)     │
└─────────────────────┘         └──────────────────────┘         └────────────────┘
      │                                  │                                │
      │  Команди:                        │  File-based queue              │  Виконує:
      │  "Імпортуй DXF"                 │  (JSON files)                  │  Transaction
      │  "Створи силос"                 │                                │  Elements
      └──────────────────────────────────┴────────────────────────────────┘
```

### Компоненти:

1. **revit_mcp_server.py** — MCP сервер (працює поза Revit)
2. **revit_listener.py** — pyRevit listener (працює ВСЕРЕДИНІ Revit)
3. **commands_queue/** — черга команд (JSON файли)
4. **results_queue/** — черга результатів (JSON файли)

---

## 📦 ВСТАНОВЛЕННЯ

### Крок 1: Встановити Autodesk Revit

**Потрібна версія:** Revit 2024 або 2025

#### Для студентів (безкоштовно):
1. Перейти на [Autodesk Education](https://www.autodesk.com/education/students)
2. Створити обліковий запис (студентський email)
3. Завантажити **Revit Student Edition**
4. Встановити (займає ~10GB)

#### Для професіоналів:
- Використати комерційну ліцензію Revit

---

### Крок 2: Встановити pyRevit

**pyRevit** — це безкоштовний плагін для Revit, який дозволяє запускати Python скрипти.

#### Встановлення:

1. **Завантажити installer:**
   - [GitHub Releases - pyRevit](https://github.com/pyrevitlabs/pyRevit/releases)
   - Вибрати останню версію (наприклад, `pyRevit_4.8.x_signed.exe`)

2. **Запустити інсталятор:**
   - Обрати версії Revit для підключення (2024, 2025)
   - Завершити встановлення

3. **Перевірити:**
   - Запустити Revit
   - В інтерфейсі має з'явитися вкладка **"pyRevit"**
   - Якщо немає — перезапустити Revit

---

### Крок 3: Встановити Python залежності для MCP Server

#### Windows:

```bash
cd "D:\autocad project\revit-mcp"
pip install -r requirements.txt
```

Це встановить:
- `mcp` — Model Context Protocol SDK
- `fastmcp` — спрощений фреймворк для MCP серверів

---

### Крок 4: Налаштувати pyRevit Listener

#### Опція A: Автоматичне розміщення скрипта

```bash
# Скопіювати revit_listener.py в pyRevit extension
xcopy /Y "D:\autocad project\revit-mcp\pyrevit_extension\revit_listener.py" "%APPDATA%\pyRevit\Extensions\revit_listener.extension\Revit.tab\Listener.panel\StartListener.pushbutton\"
```

Після цього в pyRevit з'явиться кнопка "Start Listener".

#### Опція B: Ручне розміщення

1. Відкрити папку:
   ```
   %APPDATA%\pyRevit\Extensions\
   ```

2. Створити структуру:
   ```
   MyExtension.extension/
   └── MyTab.tab/
       └── Listener.panel/
           └── StartListener.pushbutton/
               ├── script.py  (скопіювати revit_listener.py сюди)
               └── icon.png   (опціонально)
   ```

3. Перезапустити Revit або натиснути **pyRevit → Reload**

---

## 🚀 ЗАПУСК СИСТЕМИ

### Крок 1: Запустити Revit

1. Відкрити **Autodesk Revit 2024/2025**
2. Створити новий проект або відкрити існуючий
3. Зберегти проект (обов'язково!)

---

### Крок 2: Запустити pyRevit Listener

**В Revit:**

1. Перейти на вкладку **pyRevit**
2. Натиснути кнопку **"Start Listener"** (або запустити `revit_listener.py` через pyRevit Scripts)
3. В Output вікні має з'явитися:
   ```
   ✅ Revit Listener Started
   Commands Queue: D:\autocad project\revit-mcp\commands_queue
   Results Queue: D:\autocad project\revit-mcp\results_queue
   Waiting for commands from Claude Code...
   ```

**Listener працює!** Він моніторить папку `commands_queue` кожні 0.5 секунди.

---

### Крок 3: Запустити MCP Server (опціонально для тестування)

**У терміналі:**

```bash
cd "D:\autocad project\revit-mcp"
python revit_mcp_server.py
```

Побачите:
```
======================================================================
  REVIT MCP SERVER v0.1.0
  Model Context Protocol Server for Autodesk Revit
======================================================================

Commands Queue: D:\autocad project\revit-mcp\commands_queue
Results Queue:  D:\autocad project\revit-mcp\results_queue

Waiting for Claude Code to connect...
```

**Увага:** MCP Server автоматично запускається Claude Code через `.mcp.json`, тому цей крок опціональний!

---

### Крок 4: Використовувати в Claude Code

Тепер Claude Code має доступ до інструментів Revit!

**Приклад команд:**

```
Claude, ping Revit to check if it's working
```

```
Claude, import page 1 DXF file into Revit
```

```
Claude, create a new sheet named "Technological Scheme"
```

```
Claude, list all families in the project
```

---

## 🛠️ ДОСТУПНІ ІНСТРУМЕНТИ (MCP Tools)

### 1. Системні інструменти

#### `ping_revit()`
Перевірити, чи Revit listener активний.

```python
# Claude Code викличе:
ping_revit()

# Поверне:
"✅ Revit listener is ACTIVE!
Version: 2024
Document: Grain_Elevator.rvt
Response time: 0.05s"
```

#### `get_revit_info()`
Отримати детальну інформацію про проект.

```python
get_revit_info()

# Поверне:
{
  "document_name": "Grain_Elevator.rvt",
  "element_count": 1234,
  "family_count": 45,
  "sheet_count": 12,
  "view_count": 28
}
```

---

### 2. Робота з DXF файлами

#### `import_dxf(page_number, as_link=False, preserve_colors=True)`
Імпортувати DXF файл.

```python
# Імпортувати Page 01 (схему процесу)
import_dxf(page_number=1, preserve_colors=True)

# Поверне:
"✅ Successfully imported Page 01
Import ID: 12345
Type: Embedded
View: Level 1"
```

**Параметри:**
- `page_number`: 1-12 (номер сторінки з `FINAL_DXF_PERFECT_V7/`)
- `as_link`: False = вставка, True = посилання
- `preserve_colors`: Зберегти RGB кольори (синій для силосів, червоний для конвеєрів)

#### `analyze_imported_geometry(import_id)`
Проаналізувати імпортовану геометрію (LIDAR-підхід).

```python
analyze_imported_geometry(import_id="12345")

# Поверне:
{
  "layers": {
    "RGB_000_000_255": 686,  # Сині об'єкти (силоси)
    "RGB_255_000_000": 476   # Червоні (конвеєри)
  },
  "clusters": [
    {"center": (x, y), "line_count": 48, "type": "silo"},
    ...
  ]
}
```

---

### 3. Робота з Families

#### `load_family(family_path)`
Завантажити .rfa файл.

```python
load_family(family_path="D:/Families/Silo_MSVU_220.rfa")

# Поверне:
{
  "family_name": "Silo_MSVU_220",
  "symbols": ["Default", "Type 1"]
}
```

#### `place_family_instance(family_name, symbol_name, x, y, z, parameters)`
Розмістити екземпляр.

```python
place_family_instance(
    family_name="Silo_MSVU_220",
    symbol_name="Default",
    x=0,       # мм!
    y=0,       # мм!
    z=0,
    parameters={
        "Diameter": 22000,  # мм
        "Height": 21422,
        "Equipment_Tag": "МСВУ-220.13.В12"
    }
)

# Поверне:
{
  "instance_id": "98765",
  "location": {"x": 0, "y": 0, "z": 0},
  "parameters_set": ["Diameter", "Height", "Equipment_Tag"]
}
```

**Важливо:** Координати та параметри в **міліметрах** (автоматично конвертуються в фути для Revit).

#### `list_families()`
Список завантажених сімей.

```python
list_families()

# Поверне:
[
  {
    "name": "Silo_MSVU_220",
    "category": "Generic Models",
    "symbols": ["Default", "Type 1"]
  },
  ...
]
```

---

### 4. Робота з Sheets

#### `create_sheet(number, name, titleblock_name)`
Створити аркуш.

```python
create_sheet(
    number="А-01",
    name="Схема технологічного процесу",
    titleblock_name="A0 metric"
)

# Поверне:
{
  "sheet_id": "11111",
  "number": "А-01",
  "name": "Схема технологічного процесу"
}
```

#### `list_sheets()`
Список аркушів.

```python
list_sheets()

# Поверне:
[
  {"id": "11111", "number": "А-01", "name": "Схема..."},
  ...
]
```

---

### 5. Експорт

#### `export_sheets_to_pdf(sheet_numbers, output_path, combined=True)`
Експорт в PDF.

```python
export_sheets_to_pdf(
    sheet_numbers=["А-01", "А-02", "А-03"],
    output_path="D:/Output/Grain_Elevator.pdf",
    combined=True  # Один файл
)

# Поверне:
"D:/Output/Grain_Elevator.pdf"
```

---

## 📋 ПРИКЛАДИ ВИКОРИСТАННЯ

### Приклад 1: Імпорт всіх 12 DXF сторінок

```
Claude, import all 12 DXF pages from FINAL_DXF_PERFECT_V7
```

Claude Code виконає:
```python
for page in range(1, 13):
    import_dxf(page_number=page, preserve_colors=True)
```

---

### Приклад 2: Створити силос з параметрами

```
Claude, create a silo at coordinates (0, 0) with diameter 22000mm and height 21422mm
```

Claude Code виконає:
```python
# 1. Завантажити Family (якщо не завантажена)
load_family("D:/Families/Silo_MSVU_220.rfa")

# 2. Розмістити екземпляр
place_family_instance(
    family_name="Silo_MSVU_220",
    symbol_name="Default",
    x=0, y=0, z=0,
    parameters={"Diameter": 22000, "Height": 21422}
)
```

---

### Приклад 3: Генерація проекту з JSON

```
Claude, build the project from config_6_silos.json
```

Claude Code:
1. Прочитає `config_6_silos.json`
2. Викличе `build_from_config(config_path)`
3. Автоматично створить 6 силосів, конвеєри, норії, труби
4. Згенерує аркуші

---

## 🔧 НАЛАГОДЖЕННЯ

### Проблема: "Revit listener NOT RESPONDING"

**Рішення:**
1. Перевірити, чи Revit запущений
2. Перевірити, чи listener запущений (натиснути кнопку в pyRevit)
3. Перевірити шляхи до черг:
   ```
   D:\autocad project\revit-mcp\commands_queue
   D:\autocad project\revit-mcp\results_queue
   ```

---

### Проблема: "Family not found"

**Рішення:**
1. Перевірити, чи Family завантажена: `list_families()`
2. Завантажити вручну в Revit: **Insert → Load Family**
3. Або викликати: `load_family("шлях/до/сім'ї.rfa")`

---

### Проблема: "No titleblocks found"

**Рішення:**
1. Відкрити проект з titleblocks (рамками)
2. Або завантажити titleblock: **Insert → Load Family** → вибрати titleblock (.rfa)

---

## 📁 СТРУКТУРА ПРОЕКТУ

```
revit-mcp/
├── revit_mcp_server.py          # MCP сервер (головний файл)
├── pyrevit_extension/
│   └── revit_listener.py        # pyRevit listener (копіювати в Revit)
├── commands_queue/              # Черга команд (автоматично створюється)
├── results_queue/               # Черга результатів
├── requirements.txt             # Python залежності
└── README.md                    # Ця інструкція
```

---

## 🎯 НАСТУПНІ КРОКИ

### Після встановлення:

1. **Створити базові Families вручну** (5-10 штук):
   - Silo_MSVU_220.rfa (параметри: Diameter, Height, Volume)
   - Conveyor_T7.rfa (Length, Angle)
   - Elevator_H100.rfa (Height)
   - Valve_DN100.rfa (DN size)
   - Pipe_DN100.rfa (Length, Diameter)

2. **Тестувати інструменти:**
   - Ping Revit
   - Імпорт Page 01
   - Розміщення одного силосу
   - Створення аркуша

3. **Інтегрувати з config_6_silos.json:**
   - Розробити логіку `build_from_config()`
   - Автоматична генерація проекту

4. **Генерація 12 sheets:**
   - Створити шаблон аркушів
   - Розмістити види
   - Експорт в PDF

---

## 📚 КОРИСНІ ПОСИЛАННЯ

### Revit API:
- [Revit API Docs 2024](https://www.revitapidocs.com/2024/)
- [Revit API Developer Guide](https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Using_the_Autodesk_Revit_API_html)

### pyRevit:
- [pyRevit Documentation](https://docs.pyrevitlabs.io/)
- [pyRevit GitHub](https://github.com/pyrevitlabs/pyRevit)

### MCP:
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

---

## 🤝 ПІДТРИМКА

Якщо виникли проблеми:
1. Перевірити `commands_queue` та `results_queue` — чи є файли, які "застрягли"
2. Перезапустити listener в Revit
3. Перевірити логи pyRevit: **pyRevit → Settings → Output**

---

**Версія:** 0.1.0
**Ліцензія:** MIT
**Автор:** Claude Code (Anthropic Sonnet 4.5)
**Дата:** 2026-01-01

**Успішної автоматизації! 🚀**
