# 🏗️ ПРОФЕСІЙНА СИСТЕМА ГЕНЕРАЦІЇ ПРОМИСЛОВИХ СХЕМ

## 🎯 ПРОБЛЕМА:
Зараз я **хаотично малюю** без розуміння існуючої структури. Це **НЕПРИПУСТИМО** в реальних проектах, де помилка в 1 мм може коштувати мільйони!

---

## ✅ РІШЕННЯ: 3-РІВНЕВА АРХІТЕКТУРА

```
┌──────────────────────────────────────────────┐
│  РІВЕНЬ 1: АНАЛІЗ ТА ЕКСТРАКЦІЯ              │
│  - Читання всіх 12 сторінок DXF              │
│  - Розпізнавання елементів (силоси, норії)  │
│  - Витягування ТОЧНИХ координат та розмірів │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  РІВЕНЬ 2: БІБЛІОТЕКА КОМПОНЕНТІВ            │
│  - JSON база даних всіх елементів            │
│  - Параметричні шаблони                      │
│  - Граф залежностей (менший силос →          │
│    менший конвеєр → менша норія)             │
└──────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────┐
│  РІВЕНЬ 3: ГЕНЕРАТОР (DJ-МІКШЕР)             │
│  - Приймає ТЗ (7 силосів, 2×20м + 5×22м)    │
│  - Розраховує координати та з'єднання        │
│  - Генерує креслення в AutoCAD               │
└──────────────────────────────────────────────┘
```

---

## 📚 СТРУКТУРА ФАЙЛІВ:

### 1. БІБЛІОТЕКА КОМПОНЕНТІВ (JSON)

**`components_library.json`**
```json
{
  "silos": {
    "МСВУ_220.13.В12_D20": {
      "diameter": 20000,
      "height": 21000,
      "capacity": 6600,
      "outlets": 7,
      "cone_height": 3000,
      "dome_height": 2000,
      "drawing": {
        "top_view": {
          "type": "circle",
          "radius": 10000,
          "hatch": "ANSI31"
        },
        "side_view": {
          "type": "composite",
          "parts": ["cylinder", "cone", "dome"]
        }
      }
    },
    "МСВУ_220.13.В12_D22": {
      "diameter": 22000,
      "height": 22000,
      "capacity": 8400,
      "outlets": 7,
      ...
    }
  },

  "noria": {
    "H1_38m": {
      "height": 38000,
      "width": 2000,
      "capacity": 100,
      "bucket_diameter": 800,
      ...
    }
  },

  "conveyor": {
    "T_100tph": {
      "capacity": 100,
      "width": 1500,
      "arrow_size": 800,
      ...
    }
  }
}
```

---

### 2. ГРАФ ЗАЛЕЖНОСТЕЙ

**`dependencies_graph.json`**
```json
{
  "layout_2_2_3": {
    "silos": [
      {"id": 1, "type": "D20", "position": "upper_left"},
      {"id": 2, "type": "D20", "position": "upper_right"},
      {"id": 3, "type": "D22", "position": "middle_left"},
      {"id": 4, "type": "D22", "position": "middle_right"},
      {"id": 5, "type": "D22", "position": "lower_left"},
      {"id": 6, "type": "D22", "position": "lower_center"},
      {"id": 7, "type": "D22", "position": "lower_right"}
    ],

    "connections": [
      {"from": "noria_H4", "to": "silo_1", "via": "conveyor_T7"},
      {"from": "silo_1", "to": "silo_2", "via": "conveyor_T8"},
      ...
    ],

    "spacing_rules": {
      "silo_to_silo": "max(diameter1, diameter2) + 2000",
      "noria_offset": "silo.center_x - 15000",
      ...
    }
  }
}
```

---

### 3. КООРДИНАТИ З ЕТАЛОННОГО КРЕСЛЕННЯ

**`reference_coordinates.json`** (витягнуті з page_01-12.dxf)
```json
{
  "page_02": {
    "view": "top",
    "scale": "1:100",
    "elements": {
      "silo_1": {
        "center": {"x": 180, "y": 850},
        "radius": 55,
        "type": "circle",
        "label": {"text": "3", "position": {"x": 180, "y": 910}}
      },
      "silo_2": {
        "center": {"x": 300, "y": 850},
        "radius": 55,
        ...
      },
      ...
    }
  }
}
```

---

## 🎛️ СИСТЕМА ГЕНЕРАЦІЇ (DJ-МІКШЕР)

### КРОК 1: ОТРИМАННЯ ТЗ

**Приклад ТЗ:**
```python
project_spec = {
    "name": "Завод Одеса №2",
    "silos": [
        {"count": 2, "diameter": 20, "height": 21},
        {"count": 3, "diameter": 22, "height": 22},
        {"count": 2, "diameter": 24, "height": 23}  # НОВИЙ РОЗМІР!
    ],
    "layout": "2_3_2",
    "capacity_per_hour": 150,  # т/год (замість 100)
}
```

### КРОК 2: АНАЛІЗ ТА ПЛАН

```python
class SchemaGenerator:
    def analyze(self, spec):
        """Аналізує ТЗ та створює план"""

        # 1. Вибір базового шаблону
        template = self.select_template(spec["layout"])

        # 2. Масштабування компонентів
        silos = self.scale_silos(spec["silos"])
        conveyors = self.scale_conveyors(spec["capacity_per_hour"])

        # 3. Розрахунок координат
        coordinates = self.calculate_coordinates(silos, template)

        # 4. Перевірка колізій
        if self.check_collisions(coordinates):
            coordinates = self.adjust_spacing(coordinates)

        return {
            "silos": silos,
            "coordinates": coordinates,
            "connections": self.build_connections(silos)
        }
```

### КРОК 3: ГЕНЕРАЦІЯ

```python
def generate(self, plan):
    """Генерує креслення в AutoCAD"""

    acad = self.connect_autocad()

    # Малює кожен елемент з бібліотеки
    for silo in plan["silos"]:
        component = self.library["silos"][silo["type"]]
        self.draw_component(acad, component, silo["coords"])

    # Малює з'єднання
    for conn in plan["connections"]:
        self.draw_connection(acad, conn)

    # Додає оформлення
    self.add_frame(acad, plan["bounds"])
    self.add_legend(acad, plan["summary"])
```

---

## 🔬 ВИТЯГУВАННЯ ДАНИХ З PDF/DXF

### Скрипт для аналізу 12 сторінок:

```python
class DXFAnalyzer:
    def analyze_all_pages(self):
        """Аналізує всі 12 сторінок та будує бібліотеку"""

        library = {
            "silos": {},
            "noria": {},
            "conveyors": {},
            "coordinates": {}
        }

        for page_num in range(1, 13):
            dxf = self.open_dxf(f"page_{page_num:02d}.dxf")

            # Розпізнати елементи
            circles = self.find_circles(dxf)  # Силоси (вид зверху)
            rectangles = self.find_rectangles(dxf)  # Норії, конвеєри
            text = self.find_text(dxf)  # Мітки

            # Класифікувати
            silos = self.classify_silos(circles, text)
            noria = self.classify_noria(rectangles, text)

            # Додати до бібліотеки
            library["silos"].update(silos)
            library["noria"].update(noria)
            library["coordinates"][f"page_{page_num}"] = {
                "silos": [s.coords for s in silos],
                "noria": [n.coords for n in noria]
            }

        return library
```

---

## 📐 ПРИКЛАД ВИКОРИСТАННЯ

### Генерація схеми з 7 силосів:

```python
# 1. Завантажити бібліотеку (з аналізу 12 сторінок)
generator = SchemaGenerator()
generator.load_library("components_library.json")
generator.load_template("layout_2_2_3.json")

# 2. Задати ТЗ
spec = {
    "silos": [
        {"count": 2, "type": "МСВУ_D20"},
        {"count": 2, "type": "МСВУ_D22"},
        {"count": 3, "type": "МСВУ_D22"}  # 7-й силос тут!
    ],
    "noria": [
        {"type": "H1_38m", "count": 1},
        {"type": "H3_33m", "count": 1},
        ...
    ]
}

# 3. Згенерувати
plan = generator.analyze(spec)
print(plan.summary())  # Перегляд плану перед генерацією

# 4. Підтвердження
if input("Генерувати? (y/n): ") == 'y':
    generator.generate(plan)
    generator.save("Одеса_Завод2_7silos.dwg")
```

---

## 🎯 РЕЗУЛЬТАТ:

### ДО (зараз):
- ❌ Хаотичне малювання
- ❌ Неправильні координати
- ❌ Немає системи
- ❌ Кожен проект з нуля

### ПІСЛЯ (з системою):
- ✅ Професійна бібліотека компонентів
- ✅ Точні координати з еталону
- ✅ Параметрична генерація
- ✅ Новий проект за 5 хвилин
- ✅ Масштабування (6→7→10→50 силосів)
- ✅ Різні конфігурації (2-2-3, 3-3-4, тощо)

---

## 📝 НАСТУПНІ КРОКИ:

1. **ЗАРАЗ**: Проаналізувати всі 12 сторінок DXF
2. Витягти ТОЧНІ координати та розміри
3. Створити `components_library.json`
4. Створити `reference_coordinates.json`
5. Написати `SchemaGenerator`
6. Протестувати на прикладі 7 силосів

---

**ЦЕ ПРАВИЛЬНИЙ ШЛЯХ - ПРОФЕСІЙНА СИСТЕМА, А НЕ ХАОС!** 🎯
