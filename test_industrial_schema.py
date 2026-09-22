# -*- coding: utf-8 -*-
"""
ТЕСТОВИЙ СКРИПТ ДЛЯ ПРОМИСЛОВОГО MCP СЕРВЕРА
Малює приклад технологічної схеми з силосами, транспортерами та норієм
"""

# Це приклад того, як Claude Code буде використовувати MCP інструменти
# Ти можеш запустити це через MCP сервер або через Claude Code

# Приклад використання через Python (для тестування):
example_schema = {
    "schema_name": "Лінія зберігання зерна №1",
    "operations": [
        # === СИЛОСИ (3 штуки) ===
        {
            "type": "silo",
            "params": {
                "x": 0,
                "y": 0,
                "diameter": 22000,
                "height": 21422,
                "equipment_tag": "МСВУ-1 (S-101)",
                "material": "carbon_steel",
                "capacity": 100
            }
        },
        {
            "type": "silo",
            "params": {
                "x": 30000,
                "y": 0,
                "diameter": 22000,
                "height": 21422,
                "equipment_tag": "МСВУ-2 (S-102)",
                "material": "carbon_steel",
                "capacity": 100
            }
        },
        {
            "type": "silo",
            "params": {
                "x": 60000,
                "y": 0,
                "diameter": 22000,
                "height": 21422,
                "equipment_tag": "МСВУ-3 (S-103)",
                "material": "carbon_steel",
                "capacity": 100
            }
        },

        # === НОРІЙ (ЕЛЕВАТОР) ===
        {
            "type": "elevator",
            "params": {
                "x": 15000,
                "y": 25000,
                "bucket_diameter": 350,
                "lift_height": 33000,
                "equipment_tag": "H5",
                "bucket_capacity": 5.0,
                "capacity": 100
            }
        },

        {
            "type": "elevator",
            "params": {
                "x": 45000,
                "y": 25000,
                "bucket_diameter": 350,
                "lift_height": 33000,
                "equipment_tag": "H6",
                "bucket_capacity": 5.0,
                "capacity": 100
            }
        },

        # === ТРАНСПОРТЕРИ ===
        {
            "type": "conveyor",
            "params": {
                "start_x": 11000,
                "start_y": 15000,
                "end_x": 15000,
                "end_y": 25000,
                "width": 1200,
                "equipment_tag": "T7",
                "material": "rubber",
                "inclination_angle": 15,
                "capacity": 100
            }
        },

        {
            "type": "conveyor",
            "params": {
                "start_x": 15000,
                "start_y": 58000,
                "end_x": 30000,
                "end_y": 25000,
                "width": 1200,
                "equipment_tag": "T8",
                "material": "rubber",
                "inclination_angle": 0,
                "capacity": 100
            }
        },

        {
            "type": "conveyor",
            "params": {
                "start_x": 41000,
                "start_y": 15000,
                "end_x": 45000,
                "end_y": 25000,
                "width": 1200,
                "equipment_tag": "T10",
                "material": "rubber",
                "inclination_angle": 15,
                "capacity": 100
            }
        },

        {
            "type": "conveyor",
            "params": {
                "start_x": 45000,
                "start_y": 58000,
                "end_x": 60000,
                "end_y": 25000,
                "width": 1200,
                "equipment_tag": "T12",
                "material": "rubber",
                "inclination_angle": 0,
                "capacity": 100
            }
        },

        # === ТРУБОПРОВОДИ (З'ЄДНАННЯ) ===
        {
            "type": "pipe",
            "params": {
                "from_x": 11000,
                "from_y": 0,
                "to_x": 11000,
                "to_y": 15000,
                "pipe_diameter": 150,
                "tag": "P-101"
            }
        },

        {
            "type": "pipe",
            "params": {
                "from_x": 41000,
                "from_y": 0,
                "to_x": 41000,
                "to_y": 15000,
                "pipe_diameter": 150,
                "tag": "P-102"
            }
        }
    ]
}

# Приклад простої схеми (для швидкого тесту)
simple_schema = {
    "schema_name": "Проста тестова схема",
    "operations": [
        {
            "type": "silo",
            "params": {
                "x": 0,
                "y": 0,
                "diameter": 22000,
                "height": 21422,
                "equipment_tag": "S-101",
                "material": "carbon_steel",
                "capacity": 100
            }
        },
        {
            "type": "conveyor",
            "params": {
                "start_x": 25000,
                "start_y": 10000,
                "end_x": 50000,
                "end_y": 10000,
                "width": 1200,
                "equipment_tag": "T7",
                "material": "rubber",
                "inclination_angle": 0,
                "capacity": 100
            }
        },
        {
            "type": "elevator",
            "params": {
                "x": 55000,
                "y": 0,
                "bucket_diameter": 350,
                "lift_height": 33000,
                "equipment_tag": "H5",
                "bucket_capacity": 5.0,
                "capacity": 100
            }
        }
    ]
}

# Інструкції для використання в Claude Code:
"""
ЯК ВИКОРИСТАТИ ЦЕЙ ФАЙЛ В CLAUDE CODE:

1. Відкрий AutoCAD з новим малюнком (Drawing1.dwg)

2. В Claude Code скажи:

   "Використай MCP сервер autocad-industrial та намалюй технологічну схему з такими елементами:

    1. Три силоси МСВУ діаметром 22м, висотою 21.4м в позиціях (0,0), (30000,0), (60000,0) з тегами S-101, S-102, S-103

    2. Два норії висотою 33м з ковшами 350мм в позиціях (15000, 25000) та (45000, 25000) з тегами H5, H6

    3. Транспортери для з'єднання:
       - T7: від силоса 1 до норія H5
       - T8: від норія H5 до силоса 2
       - T10: від силоса 2 до норія H6
       - T12: від норія H6 до силоса 3

    4. Трубопроводи діаметром 150мм для подачі матеріалу з силосів на транспортери"

3. Або використай готову схему:

   "Намалюй технологічну схему з файлу test_industrial_schema.py, використовуючи simple_schema"

4. Для повної схеми:

   "Намалюй повну технологічну схему з файлу test_industrial_schema.py, використовуючи example_schema"

ОЧІКУВАНИЙ РЕЗУЛЬТАТ:
======================

В AutoCAD з'явиться професійна технологічна схема з:
- Силосами МСВУ з конусами та куполами
- Норіями з барабанами та ковшами
- Транспортерами зі стрічками та роликами
- Трубопроводами з стрілками напрямку
- Всіма технічними параметрами та тегами

Час малювання: ~5-10 секунд для простої схеми, ~15-20 секунд для повної.
"""

# Додаткові тестові приклади:

# ПРИКЛАД 1: Один силос
single_silo_test = """
Намалюй один силос МСВУ з такими параметрами:
- Позиція: (0, 0)
- Діаметр: 22000мм
- Висота: 21422мм
- Тег: "ТЕСТ-СИЛОС-1"
- Матеріал: вуглецева сталь
- Ємність: 100 т/год
"""

# ПРИКЛАД 2: Транспортерна система
conveyor_system_test = """
Намалюй систему транспортерів:
1. Транспортер T1: від (0, 0) до (10000, 5000), ширина 1200мм
2. Транспортер T2: від (10000, 5000) до (20000, 5000), ширина 1200мм
3. Транспортер T3: від (20000, 5000) до (30000, 0), ширина 1200мм

Всі з потужністю 100 т/год, гумова стрічка, кут нахилу 15 градусів де потрібно.
"""

# ПРИКЛАД 3: Вертикальна транспортна система
vertical_system_test = """
Створи вертикальну систему транспортування:
1. Силос S-101 в точці (0, 0), діаметр 22м, висота 21.4м
2. Норій H5 в точці (15000, 0), висота 33м, ковші 350мм
3. Силос S-102 в точці (30000, 0), діаметр 22м, висота 21.4м
4. З'єднай їх трубопроводами діаметром 150мм
"""

if __name__ == "__main__":
    print("="*60)
    print("ТЕСТОВІ СХЕМИ ДЛЯ ПРОМИСЛОВОГО MCP СЕРВЕРА")
    print("="*60)
    print("\nДоступні схеми:")
    print("1. simple_schema - Проста схема (1 силос, 1 транспортер, 1 норій)")
    print("2. example_schema - Повна схема (3 силоси, 4 транспортери, 2 норії)")
    print("\nВикористовуй ці схеми через Claude Code з MCP сервером!")
    print("="*60)
