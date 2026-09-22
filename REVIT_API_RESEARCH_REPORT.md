# 🔬 ДОСЛІДЖЕННЯ: Revit API + MCP Server для автоматизації

**Дата:** 2026-01-01
**Мета:** Розібратися з Revit API, pyRevit, та розробити концепцію MCP Server для професійного керування Revit

---

## 📚 ЧАСТИНА 1: Revit API - Що це і як працює

### Основи Revit API

**Revit API** — це .NET-based API від Autodesk, який дозволяє автоматизувати Revit через C# або Python (IronPython/CPython).

#### Ключові компоненти:

1. **Namespaces (простори імен):**
   ```
   Autodesk.Revit.DB         → Робота з базою даних моделі (Document, Element, Transaction)
   Autodesk.Revit.UI         → Інтерфейс користувача (UIDocument, Selection)
   Autodesk.Revit.Creation   → Створення елементів (NewFamilyInstance, NewLine)
   ```

2. **Головні класи:**
   - **Document** — поточний Revit проект (.rvt файл)
   - **Transaction** — обов'язкова обгортка для будь-яких змін
   - **Element** — базовий клас для всіх об'єктів (Wall, Family, Sheet)
   - **FamilyInstance** — екземпляр сім'ї (параметричний об'єкт)
   - **View/ViewSheet** — види та аркуші креслень

3. **Transaction Model (критично!):**
   ```python
   # ВСІ зміни в Revit МАЮТЬ бути всередині Transaction
   t = Transaction(doc, "Назва операції")
   t.Start()
   # ... ваші зміни тут ...
   t.Commit()  # або t.RollBack() при помилці
   ```

#### Офіційна документація:
- [Revit API 2025 Developer Guide](https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Using_the_Autodesk_Revit_API_html)
- [Revit API Docs 2024](https://www.revitapidocs.com/2024/) (community)
- [Autodesk Platform Services - Revit](https://aps.autodesk.com/developer/overview/revit)

---

## 🐍 ЧАСТИНА 2: pyRevit - Python всередині Revit

### Що таке pyRevit?

**pyRevit** — це безкоштовний open-source плагін, який дозволяє писати Python скрипти всередині Revit **без компіляції**.

#### Ключові можливості:

1. **Rapid Application Development (RAD):**
   - Пишеш `.py` файл → натискаєш кнопку в Revit → скрипт виконується
   - Не потрібно компілювати DLL як в C#
   - Підтримує IronPython (Python 2.7) та CPython (Python 3.8+)

2. **Доступ до Revit API:**
   ```python
   # pyRevit автоматично надає змінні:
   doc = __revit__.ActiveUIDocument.Document  # Поточний документ
   uidoc = __revit__.ActiveUIDocument         # UI Document
   app = __revit__.Application                # Revit Application

   from pyrevit import revit, DB, forms, script

   # Transaction wrapper (спрощений)
   with revit.Transaction("Створити силос"):
       # Ваші зміни тут
       pass
   ```

3. **Інструменти для автоматизації:**
   - **Selection** — вибір елементів
   - **Forms** — діалоги для користувача
   - **Script** — логування, налагодження
   - **DB** — доступ до Autodesk.Revit.DB

#### Встановлення:
```bash
# Завантажити з https://github.com/pyrevitlabs/pyRevit/releases
# Запустити інсталятор → обрати версії Revit (2024, 2025)
```

#### Приклад скрипта:
```python
# -*- coding: utf-8 -*-
"""Створити силоси з JSON конфігурації"""

from pyrevit import revit, DB, forms, script
import json

# Читання конфігурації
with open('config_6_silos.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Transaction
with revit.Transaction("Створити силоси"):
    for silo_data in config['equipment']['silos']:
        # Завантажити Family Symbol (тип сім'ї)
        symbol = None  # TODO: знайти через FilteredElementCollector

        # Створити екземпляр
        point = DB.XYZ(
            silo_data['x'] / 304.8,  # мм → фути (Revit внутрішні одиниці!)
            silo_data['y'] / 304.8,
            0
        )

        instance = doc.Create.NewFamilyInstance(
            point, symbol, level,
            DB.Structure.StructuralType.NonStructural
        )

        # Встановити параметри
        instance.LookupParameter("Diameter").Set(silo_data['diameter'] / 304.8)
        instance.LookupParameter("Height").Set(silo_data['height'] / 304.8)
        instance.LookupParameter("Equipment_Tag").Set(silo_data['tag'])

forms.alert("Створено {} силосів!".format(len(config['equipment']['silos'])))
```

#### Навчальні ресурси:
- [pyRevit Official Docs](https://docs.pyrevitlabs.io/)
- [Learn Revit API Course](https://www.learnrevitapi.com/) (платний, але якісний)
- [8 Steps to Get Started with Revit API and Python](https://www.bimpure.com/blog/8-tips-to-get-started-with-revit-api-and-python)
- [Getting Started with pyRevit](https://archilabs.ai/posts/getting-started-with-pyrevit)

---

## 📥 ЧАСТИНА 3: Імпорт DXF/CAD файлів в Revit через API

### Проблема: Як програмно імпортувати наші 12 DXF файлів?

#### Метод 1: Document.Import() (вставка як entities)
```csharp
// C# приклад (для розуміння)
DWGImportOptions options = new DWGImportOptions();
options.AutoCorrectAlmostVHLines = false;
options.ColorMode = ImportColorMode.Preserved;  // Зберегти кольори!
options.OrientToView = true;

ElementId importId;
Transaction t = new Transaction(doc, "Import DXF");
t.Start();
doc.Import("D:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_01.dxf",
           options, doc.ActiveView, out importId);
t.Commit();

// Отримати ImportInstance
ImportInstance importInst = doc.GetElement(importId) as ImportInstance;
```

#### Python еквівалент (pyRevit):
```python
from pyrevit import revit, DB
import clr
clr.AddReference('RevitAPI')

# Налаштування імпорту
options = DB.DWGImportOptions()
options.AutoCorrectAlmostVHLines = False
options.ColorMode = DB.ImportColorMode.Preserved
options.OrientToView = True
options.Unit = DB.ImportUnit.Millimeter  # ВАЖЛИВО: наші DXF в мм!

# Імпорт
file_path = r"D:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf"

with revit.Transaction("Імпортувати Page 01"):
    # Revit API має різні методи для різних версій
    # Новіший спосіб (2024+):
    import_id = clr.Reference[DB.ElementId]()
    doc.Import(file_path, options, doc.ActiveView, import_id)

    # Отримати ImportInstance
    import_inst = doc.GetElement(import_id.Value)
    print("Імпортовано: {}".format(import_inst.Id))
```

#### Метод 2: Document.Link() (посилання на зовнішній файл)
```python
# Створює link замість embedding — файл залишається зовнішнім
link_id = clr.Reference[DB.ElementId]()
doc.Link(file_path, options, doc.ActiveView, link_id)
```

#### Різниця:
- **Import** — вставляє геометрію в проект (статично)
- **Link** — посилання на зовнішній файл (оновлюється при зміні DXF)

#### Для нашого випадку:
**Рекомендація:** Використати **Import**, бо ми хочемо:
1. Проаналізувати геометрію (LIDAR-підхід)
2. Конвертувати лінії → Families
3. Видалити оригінальний DXF після конвертації

#### Джерела:
- [ImportInstance Create Method](https://www.revitapidocs.com/2018/e0fa547e-65ad-7c72-30c0-2592d181811e.htm)
- [DWGImportOptions Members](https://www.revitapidocs.com/2019/73b7f0c5-a18a-0051-0be9-5f067415b718.htm)
- [The Building Coder: Import DWG](https://thebuildingcoder.typepad.com/blog/2008/11/adding-a-shared-parameter-to-a-dwg-file.html)

---

## 🔌 ЧАСТИНА 4: Model Context Protocol (MCP) - Міст між Claude і Revit

### Що таке MCP?

**MCP (Model Context Protocol)** — це відкритий стандарт від Anthropic, який дозволяє Claude підключатися до зовнішніх інструментів через Python сервери.

#### Архітектура MCP:

```
┌─────────────────┐         ┌──────────────┐         ┌────────────────┐
│  Claude Code    │ ◄─────► │  MCP Server  │ ◄─────► │  Revit API     │
│  (Ти/Claude)    │  stdio  │  (Python)    │  COM    │  (pyRevit)     │
└─────────────────┘         └──────────────┘         └────────────────┘
      │                            │                          │
      │  Команди:                  │  Конвертує в             │  Виконує:
      │  "Створи силос"            │  Revit API calls         │  Transaction
      │  "Імпортуй DXF"           │                          │  CreateInstance
      └────────────────────────────┴──────────────────────────┘
```

### Як працює MCP Server:

1. **Claude викликає інструмент** (наприклад, `create_silo(x=0, y=0, diameter=22000)`)
2. **MCP Server отримує виклик** через stdio
3. **Server передає команду в Revit** (через pyRevit listener або COM API)
4. **Revit виконує операцію** (створює об'єкт)
5. **Server повертає результат** Claude (успіх/помилка)

### FastMCP Framework:

**FastMCP** — спрощений Python фреймворк для створення MCP серверів.

#### Приклад (базовий):
```python
# weather_server.py - простий приклад з документації
from mcp import FastMCP

# Створити сервер
mcp = FastMCP("Weather Service")

@mcp.tool()
def get_weather(city: str) -> str:
    """
    Отримати погоду для міста

    Args:
        city: Назва міста
    """
    # Тут API виклик до weather service
    return f"Weather in {city}: Sunny, 25°C"

# Запуск
if __name__ == "__main__":
    mcp.run()
```

#### Конфігурація в Claude Desktop (.mcp.json):
```json
{
  "mcpServers": {
    "weather": {
      "command": "python",
      "args": ["weather_server.py"],
      "env": {}
    }
  }
}
```

### Компоненти MCP Server:

1. **Tools** — функції, які Claude може викликати:
   ```python
   @mcp.tool()
   def create_silo(x: float, y: float, diameter: float):
       """Створити силос в Revit"""
       # Логіка тут
   ```

2. **Resources** — дані, які Claude може читати:
   ```python
   @mcp.resource("config://silos")
   def get_silo_config():
       """Повернути JSON конфігурацію силосів"""
       with open('config_6_silos.json') as f:
           return f.read()
   ```

3. **Prompts** — шаблони для Claude:
   ```python
   @mcp.prompt()
   def analyze_dxf():
       """Промпт для аналізу DXF"""
       return "Analyze the imported DXF and identify silo clusters..."
   ```

#### Джерела:
- [MCP Official Documentation](https://modelcontextprotocol.io/quickstart/server)
- [How to Use MCP with Claude](https://www.codecademy.com/article/how-to-use-model-context-protocol-mcp-with-claude-step-by-step-guide-with-examples)
- [Your First MCP Server in Python](https://dev.to/marioflores7/your-first-mcp-server-in-python-connect-custom-tools-to-claude-1hbn)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [How to Build MCP Server - Complete Guide](https://scrapfly.io/blog/posts/how-to-build-an-mcp-server-in-python-a-complete-guide)

---

## 🏗️ ЧАСТИНА 5: АРХІТЕКТУРА Revit MCP Server (Наш проект)

### Концепція: Як з'єднати Claude → MCP → Revit?

#### Проблема:
- **MCP Server** — це Python процес (може бути локальний або віддалений)
- **Revit API** — доступний тільки ВСЕРЕДИНІ процесу Revit
- **pyRevit** — працює ВСЕРЕДИНІ Revit як плагін

#### Рішення: Гібридна архітектура

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLAUDE CODE                                 │
│  (Аналізує, планує, викликає MCP інструменти)                       │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ stdio (JSON-RPC)
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       MCP SERVER (Python)                            │
│  Файл: revit_mcp_server.py                                          │
│                                                                       │
│  Інструменти:                                                        │
│  - import_dxf(page_number)        → Імпорт DXF файлу                │
│  - analyze_geometry()             → Аналіз геометрії (clusters)     │
│  - create_silo_family(params)     → Створити Silo Family            │
│  - place_silo(x, y, type)         → Розмістити силос                │
│  - create_sheet(number, name)     → Створити аркуш                  │
│  - export_pdf(sheet_numbers)      → Експорт в PDF                   │
│                                                                       │
│  Комунікація з Revit:                                               │
│  - Варіант A: HTTP/WebSocket listener в pyRevit                     │
│  - Варіант B: File-based queue (JSON файли)                         │
│  - Варіант C: Named pipes (Windows)                                 │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ HTTP/JSON або File Queue
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    pyRevit LISTENER (Python)                         │
│  Файл: revit_listener.py (запущений в Revit як плагін)             │
│                                                                       │
│  Функції:                                                            │
│  - Слухає команди від MCP Server                                    │
│  - Виконує Revit API операції всередині Transaction                 │
│  - Повертає результати (success/error, screenshots, ElementId)      │
│                                                                       │
│  Приклад:                                                            │
│  1. Отримує: {"action": "import_dxf", "file": "page_01.dxf"}       │
│  2. Виконує: Transaction → doc.Import(file, options, view, id)      │
│  3. Повертає: {"status": "ok", "import_id": "12345"}                │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ Revit API
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         REVIT 2024/2025                              │
│  (.rvt проект з нашими 12 sheets, families, геометрія)             │
└──────────────────────────────────────────────────────────────────────┘
```

### Варіанти комунікації MCP ↔ pyRevit:

#### Варіант A: HTTP/WebSocket (Рекомендую!)

**pyRevit Listener:**
```python
# revit_listener.py (запущений в Revit через pyRevit startup script)
from flask import Flask, request, jsonify
from pyrevit import revit, DB
import threading

app = Flask(__name__)

@app.route('/api/import_dxf', methods=['POST'])
def import_dxf():
    data = request.json
    file_path = data['file_path']

    # Виконати в Revit
    with revit.Transaction("Import DXF"):
        options = DB.DWGImportOptions()
        options.Unit = DB.ImportUnit.Millimeter

        import_id = clr.Reference[DB.ElementId]()
        doc.Import(file_path, options, doc.ActiveView, import_id)

        return jsonify({
            'status': 'ok',
            'import_id': str(import_id.Value)
        })

# Запуск в окремому потоці (щоб не блокувати Revit UI)
def start_server():
    app.run(host='127.0.0.1', port=5000)

thread = threading.Thread(target=start_server, daemon=True)
thread.start()
```

**MCP Server:**
```python
# revit_mcp_server.py
from mcp import FastMCP
import requests

mcp = FastMCP("Revit Automation")

REVIT_API_URL = "http://127.0.0.1:5000/api"

@mcp.tool()
def import_dxf(page_number: int) -> str:
    """
    Імпортувати DXF файл в Revit

    Args:
        page_number: Номер сторінки (1-12)
    """
    file_path = f"D:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_{page_number:02d}.dxf"

    response = requests.post(f"{REVIT_API_URL}/import_dxf", json={
        'file_path': file_path
    })

    result = response.json()
    if result['status'] == 'ok':
        return f"Successfully imported page {page_number}, ImportInstance ID: {result['import_id']}"
    else:
        return f"Error: {result.get('error', 'Unknown error')}"
```

#### Варіант B: File-based Queue (Простіший, але повільніший)

**Принцип:**
1. MCP Server пише команди в JSON файл: `commands_queue/cmd_001.json`
2. pyRevit Listener моніторить папку (FileSystemWatcher)
3. Виконує команди і пише результат: `results_queue/cmd_001_result.json`
4. MCP Server читає результат

**Плюси:** Просто реалізувати, не потрібен Flask
**Мінуси:** Повільніше (~100-200ms затримка), файли на диску

#### Варіант C: Named Pipes (Windows-специфічний)

Використання Windows Named Pipes для IPC (inter-process communication).
**Плюси:** Швидко, надійно
**Мінуси:** Складніша реалізація

---

## 🛠️ ЧАСТИНА 6: Інструменти (Tools) для Revit MCP Server

### Список інструментів, які потрібно реалізувати:

#### 1. Робота з DXF файлами:

```python
@mcp.tool()
def import_dxf(page_number: int, as_link: bool = False) -> dict:
    """
    Імпортувати DXF файл в активний вигляд Revit

    Args:
        page_number: Номер сторінки (1-12)
        as_link: Імпортувати як link (True) або embed (False)

    Returns:
        {'status': 'ok', 'import_id': '12345', 'entity_count': 46955}
    """
    pass

@mcp.tool()
def analyze_import_geometry(import_id: str) -> dict:
    """
    Проаналізувати імпортовану геометрію (LIDAR-підхід)

    Args:
        import_id: ID ImportInstance

    Returns:
        {
            'layers': {'RGB_000_000_255': 686, 'RGB_255_000_000': 476, ...},
            'clusters': [
                {'center': (x, y), 'line_count': 48, 'type': 'silo'},
                ...
            ],
            'bounding_box': {'min': (x1, y1), 'max': (x2, y2)}
        }
    """
    pass
```

#### 2. Робота з Families (параметричні об'єкти):

```python
@mcp.tool()
def create_silo_family(
    name: str,
    diameter: float,
    height: float,
    save_path: str
) -> str:
    """
    Створити параметричну Silo Family (.rfa файл)

    Args:
        name: Ім'я сім'ї, напр. "Silo_MSVU_220"
        diameter: Діаметр в мм (параметр)
        height: Висота в мм (параметр)
        save_path: Шлях для збереження .rfa

    Returns:
        'Successfully created family: Silo_MSVU_220.rfa'
    """
    pass

@mcp.tool()
def load_family(family_path: str) -> str:
    """
    Завантажити Family в поточний проект

    Args:
        family_path: Шлях до .rfa файлу

    Returns:
        'Loaded family: Silo_MSVU_220, FamilySymbol ID: 98765'
    """
    pass

@mcp.tool()
def place_family_instance(
    family_name: str,
    type_name: str,
    x: float,
    y: float,
    z: float,
    parameters: dict
) -> dict:
    """
    Розмістити екземпляр Family в проекті

    Args:
        family_name: Ім'я сім'ї
        type_name: Тип (напр. "Default")
        x, y, z: Координати в мм (конвертуються в фути)
        parameters: Словник параметрів, напр. {"Diameter": 22000, "Height": 21422}

    Returns:
        {'status': 'ok', 'instance_id': '45678', 'location': (x, y, z)}
    """
    pass
```

#### 3. Робота з Sheets (аркуші креслень):

```python
@mcp.tool()
def create_sheet(
    number: str,
    name: str,
    titleblock_name: str = "A0"
) -> dict:
    """
    Створити новий аркуш креслення

    Args:
        number: Номер аркуша, напр. "А-01"
        name: Назва, напр. "Схема технологічного процесу"
        titleblock_name: Тип рамки (A0, A1, A2, ...)

    Returns:
        {'status': 'ok', 'sheet_id': '11111', 'number': 'А-01'}
    """
    pass

@mcp.tool()
def place_view_on_sheet(
    sheet_id: str,
    view_id: str,
    x: float,
    y: float
) -> str:
    """
    Розмістити вигляд (view) на аркуші

    Args:
        sheet_id: ID аркуша
        view_id: ID виду
        x, y: Координати на аркуші (в мм)

    Returns:
        'Placed view on sheet, Viewport ID: 22222'
    """
    pass
```

#### 4. Експорт:

```python
@mcp.tool()
def export_sheets_to_pdf(
    sheet_numbers: list,
    output_path: str
) -> str:
    """
    Експортувати аркуші в PDF

    Args:
        sheet_numbers: Список номерів аркушів, напр. ["А-01", "А-02"]
        output_path: Шлях для збереження PDF

    Returns:
        'Exported 2 sheets to: D:/output/project.pdf'
    """
    pass

@mcp.tool()
def get_sheet_screenshot(sheet_id: str, save_path: str) -> str:
    """
    Зробити скріншот аркуша для Claude (візуальна перевірка)

    Args:
        sheet_id: ID аркуша
        save_path: Шлях для збереження PNG

    Returns:
        'Screenshot saved: D:/temp/sheet_A01.png'
    """
    pass
```

#### 5. Утиліти:

```python
@mcp.tool()
def list_all_families() -> list:
    """
    Отримати список всіх завантажених сімей в проекті

    Returns:
        [
            {'name': 'Silo_MSVU_220', 'category': 'Generic Models', 'types': ['Default', 'Type1']},
            ...
        ]
    """
    pass

@mcp.tool()
def get_project_info() -> dict:
    """
    Отримати інформацію про поточний проект

    Returns:
        {
            'name': 'Grain_Elevator.rvt',
            'revit_version': '2024',
            'sheet_count': 12,
            'family_count': 45
        }
    """
    pass
```

---

## 📋 ЧАСТИНА 7: План реалізації (Покроковий)

### Фаза 0: Підготовка (1 день)

1. **Встановити Revit Student Edition**
   - Завантажити з [Autodesk Education](https://www.autodesk.com/education/students)
   - Встановити Revit 2024 або 2025

2. **Встановити pyRevit**
   - Завантажити [pyRevit installer](https://github.com/pyrevitlabs/pyRevit/releases)
   - Запустити, обрати Revit 2024
   - Перезапустити Revit → перевірити вкладку "pyRevit"

3. **Тестовий скрипт:**
   ```python
   # test_pyrevit.py
   from pyrevit import revit, forms

   forms.alert("pyRevit працює! Revit Version: {}".format(
       __revit__.Application.VersionNumber
   ))
   ```

### Фаза 1: Простий MCP Server (2-3 дні)

**Мета:** Створити мінімальний MCP сервер, який може викликати одну функцію в Revit.

#### Крок 1.1: MCP Server (базовий)
```python
# revit_mcp_server.py
from mcp import FastMCP
import json
import os

mcp = FastMCP("Revit Automation v0.1")

COMMANDS_QUEUE = "D:\\autocad project\\revit_commands_queue"
RESULTS_QUEUE = "D:\\autocad project\\revit_results_queue"

os.makedirs(COMMANDS_QUEUE, exist_ok=True)
os.makedirs(RESULTS_QUEUE, exist_ok=True)

@mcp.tool()
def ping_revit() -> str:
    """
    Перевірити, чи Revit listener активний
    """
    import time
    cmd_id = str(int(time.time() * 1000))

    # Записати команду
    with open(f"{COMMANDS_QUEUE}/cmd_{cmd_id}.json", 'w') as f:
        json.dump({'action': 'ping', 'cmd_id': cmd_id}, f)

    # Чекати результат (timeout 5 sec)
    for _ in range(50):
        result_file = f"{RESULTS_QUEUE}/cmd_{cmd_id}_result.json"
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            os.remove(result_file)  # Очистити
            return result['message']
        time.sleep(0.1)

    return "ERROR: Revit listener not responding"

if __name__ == "__main__":
    mcp.run()
```

#### Крок 1.2: pyRevit Listener (базовий)
```python
# revit_listener.py
# Розмістити в: %APPDATA%\pyRevit\Extensions\MyExtension.extension\MyTab.tab\Listener.panel\
from pyrevit import revit, script
import os
import json
import time
import threading

COMMANDS_QUEUE = r"D:\autocad project\revit_commands_queue"
RESULTS_QUEUE = r"D:\autocad project\revit_results_queue"

logger = script.get_logger()

def process_commands():
    """Моніторити команди та виконувати"""
    while True:
        try:
            for filename in os.listdir(COMMANDS_QUEUE):
                if filename.endswith('.json'):
                    cmd_file = os.path.join(COMMANDS_QUEUE, filename)

                    with open(cmd_file, 'r') as f:
                        cmd = json.load(f)

                    # Виконати команду
                    if cmd['action'] == 'ping':
                        result = {
                            'status': 'ok',
                            'message': 'Revit listener is alive! Version: {}'.format(
                                __revit__.Application.VersionNumber
                            )
                        }
                    else:
                        result = {'status': 'error', 'message': 'Unknown action'}

                    # Записати результат
                    result_file = os.path.join(
                        RESULTS_QUEUE,
                        f"cmd_{cmd['cmd_id']}_result.json"
                    )
                    with open(result_file, 'w') as f:
                        json.dump(result, f)

                    # Видалити команду
                    os.remove(cmd_file)
                    logger.info("Processed command: {}".format(cmd['action']))

        except Exception as e:
            logger.error("Error: {}".format(e))

        time.sleep(0.5)  # Перевірка кожні 500ms

# Запустити в фоновому потоці
listener_thread = threading.Thread(target=process_commands, daemon=True)
listener_thread.start()

script.get_output().print_md("# Revit Listener Started ✅\nMonitoring: {}".format(COMMANDS_QUEUE))
```

#### Крок 1.3: Тестування
```bash
# 1. Запустити Revit → відкрити тестовий проект
# 2. У Revit: запустити revit_listener.py скрипт (pyRevit кнопка)
# 3. У терміналі: запустити MCP server
python revit_mcp_server.py

# 4. У Claude Code: викликати інструмент
# Claude → ping_revit() → Повинно повернути "Revit listener is alive! Version: 2024"
```

### Фаза 2: Імпорт DXF + Аналіз (3-4 дні)

**Мета:** Реалізувати import_dxf() та analyze_import_geometry()

#### Додати в MCP Server:
```python
@mcp.tool()
def import_dxf(page_number: int) -> str:
    """Імпортувати DXF файл"""
    cmd_id = generate_cmd_id()
    file_path = f"D:\\autocad project\\FINAL_DXF_PERFECT_V7\\page_{page_number:02d}.dxf"

    write_command(cmd_id, {
        'action': 'import_dxf',
        'file_path': file_path,
        'page_number': page_number
    })

    result = wait_for_result(cmd_id)
    return result['message']
```

#### Додати в pyRevit Listener:
```python
elif cmd['action'] == 'import_dxf':
    with revit.Transaction("Import DXF"):
        options = DB.DWGImportOptions()
        options.Unit = DB.ImportUnit.Millimeter
        options.ColorMode = DB.ImportColorMode.Preserved
        options.OrientToView = True

        import_id = clr.Reference[DB.ElementId]()
        doc.Import(cmd['file_path'], options, doc.ActiveView, import_id)

        result = {
            'status': 'ok',
            'message': f"Imported page {cmd['page_number']}",
            'import_id': str(import_id.Value)
        }
```

### Фаза 3: Створення Families (5-7 днів)

**Найскладніша частина!** Створення параметричних Families програмно.

**Альтернатива:** Створити Families вручну в Revit Family Editor, зберегти як `.rfa`, потім тільки завантажувати/розміщувати через API.

### Фаза 4: Генерація Sheets (2-3 дні)

Створення аркушів, розміщення видів, експорт PDF.

### Фаза 5: Інтеграція з існуючою системою (2-3 дні)

Підключити до `config_6_silos.json`, автоматична генерація всіх 12 сторінок.

---

## 🎯 ВИСНОВКИ ТА РЕКОМЕНДАЦІЇ

### Що ми дізналися:

1. **Revit API** — потужний, але складний (Transaction model, .NET, фути замість мм)
2. **pyRevit** — відмінний інструмент для Python автоматизації в Revit
3. **MCP Server** — ідеальний міст між Claude і Revit
4. **Імпорт DXF** — можливий через `Document.Import()`, зберігає кольори та шари
5. **Families** — найскладніша частина, можливо краще створити вручну

### Критичні виклики:

⚠️ **Виклик 1: Складність Revit API**
- Потрібно навчання (2-3 дні мінімум)
- Transaction model обов'язковий
- Конвертація одиниць (мм → фути)

⚠️ **Виклик 2: Створення Families програмно**
- Дуже складно (Revit Family API — окремий API всередині API!)
- Альтернатива: створити вручну 5-10 базових Families

⚠️ **Виклик 3: Комунікація MCP ↔ Revit**
- Revit API працює тільки ВСЕРЕДИНІ процесу Revit
- Потрібен listener (HTTP або file queue)

### Оптимальна стратегія:

#### План A: Гібридний підхід (РЕКОМЕНДУЮ для вашого випадку)

**Що робимо:**
1. **Використати AutoCAD MCP (що вже працює)** для швидкого прототипу
2. **Паралельно вивчити Revit** (встановити, зробити тестові скрипти)
3. **Створити 5-10 базових Families ВРУЧНУ** в Revit Family Editor:
   - Silo_MSVU_220.rfa
   - Conveyor_T7.rfa
   - Elevator_H100.rfa
   - Valve_Basic.rfa
   - Pipe_DN100.rfa
4. **Розробити Revit MCP Server** для розміщення цих Families з JSON
5. **Імпортувати DXF як reference** (підкладку) для позиціонування

**Переваги:**
- ✅ Швидкий старт (AutoCAD працює зараз)
- ✅ Навчання Revit поступово (не блокує прогрес)
- ✅ Families вручну — простіше і якісніше
- ✅ MCP сервер — повторне використання коду

**Часові оцінки:**
- **Тиждень 1:** AutoCAD++ (як у попередньому плані) → працюючий прототип
- **Тиждень 2:** Навчання Revit + створення 5 Families вручну
- **Тиждень 3:** Revit MCP Server + імпорт DXF + розміщення Families
- **Тиждень 4:** Генерація 12 sheets + експорт PDF

#### План B: Тільки Revit (якщо хочете відразу BIM)

**Часові оцінки:**
- **Тиждень 0:** Навчання Revit basics (tutorials)
- **Тиждень 1-2:** Створення Families вручну + pyRevit basics
- **Тиждень 3-4:** MCP Server + автоматизація
- **Тиждень 5-6:** Генерація всіх 12 сторінок

---

## 📦 Наступні кроки (ЩО РОБИТИ ЗАРАЗ)

### Варіант 1: Якщо обираєте ПЛАН A (Гібридний)

**Зараз:**
1. Продовжити розробку AutoCAD++ (Фаза 1 з DXF_STRUCTURE_ANALYSIS.md)
2. Паралельно: встановити Revit Student Edition
3. Запустити тестовий pyRevit скрипт

**Через тиждень:**
- Переключитися на Revit MCP Server

### Варіант 2: Якщо обираєте ПЛАН B (Тільки Revit)

**Зараз:**
1. Встановити Revit + pyRevit (Фаза 0)
2. Створити простий MCP Server (Фаза 1) — test ping
3. Імпортувати page_01.dxf через API (Фаза 2)

**Що я можу зробити:**
- Створити прототип `revit_mcp_server.py` + `revit_listener.py`
- Написати конфігурацію `.mcp.json`
- Підготувати структуру папок

### 🚀 МОЯ РЕКОМЕНДАЦІЯ:

**ПЛАН A (Гібридний)** — оптимальний для вашої ситуації:
- Ви отримаєте результат ШВИДКО (AutoCAD працює)
- Навчитеся Revit БЕЗ блокування прогресу
- Зможете порівняти AutoCAD vs Revit на практиці
- Families вручну — якісніше і простіше

**Готовий почати будь-який з планів!**

Скажіть:
- **"Продовжуй AutoCAD++"** → я створю `recognize_page01.py`
- **"Почни Revit MCP Server"** → я створю прототип серверу
- **"Обидва паралельно"** → розділимо задачі

---

## 📚 Джерела (Sources)

### Revit API Documentation:
- [Revit API 2025 Developer Guide](https://help.autodesk.com/view/RVT/2025/ENU/?guid=Revit_API_Revit_API_Developers_Guide_Introduction_Getting_Started_Using_the_Autodesk_Revit_API_html)
- [Revit API Docs 2024](https://www.revitapidocs.com/2024/)
- [Autodesk Platform Services - Revit](https://aps.autodesk.com/developer/overview/revit)

### pyRevit:
- [pyRevit Official Documentation](https://docs.pyrevitlabs.io/)
- [8 Steps to Get Started with Revit API and Python](https://www.bimpure.com/blog/8-tips-to-get-started-with-revit-api-and-python)
- [Getting Started with pyRevit to Automate BIM Workflows](https://archilabs.ai/posts/getting-started-with-pyrevit)
- [Learn Revit API Course](https://www.learnrevitapi.com/)
- [GitHub - pyRevit Repository](https://github.com/pyrevitlabs/pyRevit)

### Revit API Code Examples:
- [Revit API using Python - Example](https://giobel.github.io/Dynamo-Python-Example/)
- [RevitPythonShell: Families](http://wiki.theprovingground.org/revit-api-py-family)
- [The Building Coder: Family](https://thebuildingcoder.typepad.com/blog/family/)
- [FamilyInstance Class Documentation](https://www.revitapidocs.com/2018/0d2231f8-91e6-794f-92ae-16aad8014b27.htm)

### DXF/CAD Import:
- [ImportInstance Create Method](https://www.revitapidocs.com/2018/e0fa547e-65ad-7c72-30c0-2592d181811e.htm)
- [DWGImportOptions Members](https://www.revitapidocs.com/2019/73b7f0c5-a18a-0051-0be9-5f067415b718.htm)
- [The Building Coder: Adding Shared Parameter to DWG](https://thebuildingcoder.typepad.com/blog/2008/11/adding-a-shared-parameter-to-a-dwg-file.html)

### Model Context Protocol (MCP):
- [MCP Official Documentation - Build a Server](https://modelcontextprotocol.io/quickstart/server)
- [How to Use MCP with Claude - Codecademy](https://www.codecademy.com/article/how-to-use-model-context-protocol-mcp-with-claude-step-by-step-guide-with-examples)
- [Your First MCP Server in Python](https://dev.to/marioflores7/your-first-mcp-server-in-python-connect-custom-tools-to-claude-1hbn)
- [MCP Python SDK - GitHub](https://github.com/modelcontextprotocol/python-sdk)
- [How to Build MCP Server - Complete Guide](https://scrapfly.io/blog/posts/how-to-build-an-mcp-server-in-python-a-complete-guide)
- [Model Context Protocol Servers - GitHub](https://github.com/modelcontextprotocol/servers)
- [Introducing Model Context Protocol - Anthropic](https://www.anthropic.com/news/model-context-protocol)

---

**Версія:** 1.0
**Дата:** 2026-01-01
**Автор:** Claude Code (Sonnet 4.5)
