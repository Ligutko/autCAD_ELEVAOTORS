# Крок 2а (одна дрібна правка, більше нічого не роби)

Робоча папка: `D:\autocad_grok_wt\t1-components`. Ліміт: 15 хвилин, 40 викликів інструментів.

У файлі `world/kit/data/iec_motor_frames.json`:

1. Додай типорозмір **225S** (4-полюсний, 37 кВт) у `frames`: H, A, B, C, K, D, E, L, AC та решта полів у тому ж форматі, що й інші рядки, з `src` (WEG W22 p.57) і `src2` (Siemens D 81.1 p.2/122-2/123) та поясненням розбіжностей. PDF лежать у `research/design/components/sources/`.
2. У `kw_to_frame` додай `37 -> 225S` (WEG p.46 і Siemens p.2/19) та рядки `4.2` і `33`. Це нестандартні потужності з реєстру, правило: округлити вгору до найближчого стандартного ряду IEC (4.2 -> 5.5 кВт -> 132S; 33 -> 37 кВт -> 225S). У `note` запиши, що це інженерне рішення, а не дані каталогу.
3. Перевір у `world/kit/components.py`, як береться типорозмір, щоб `iec_motor(4.2)` і `iec_motor(33)` давали 132S і 225S. Якщо потрібна правка, зроби мінімальну.

Числа читай зі збережених PDF, не вигадуй. Чого не знайшов, познач `NOT_FOUND`.

Запуск Blender для перевірки: `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe --background --python <скрипт>`. Скрипт пиши у файл, не в heredoc. Приклад скрипта: `sys.path.insert(0, r"D:\autocad_grok_wt\t1-components\world")`, далі `from kit import components as k; k.iec_motor(33)`.

Наприкінці виведи 10 рядків: що змінено, значення нового рядка 225S, що не вдалося.
