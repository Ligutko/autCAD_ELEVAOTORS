# Завдання C0 для хмарного Claude Code: чи працює наш конвеєр у хмарі (проба, без розробки)

Репозиторій: `ligutko/autCAD_ELEVAOTORS`, гілка `master`. Ліміт: 40 хвилин. Мова звіту: українська.

## Навіщо
Ми хочемо давати тобі задачі з 3D-моделі елеватора (Blender, Python). Кожна зміна в нас проходить перевірки `world/build/check_*.py`, які запускаються **в Blender** (`bpy`, `mathutils`). Спершу треба з'ясувати, що з цього реально працює у твоєму середовищі. Нічого в коді моделі не змінюй.

## Кроки (по черзі; якщо крок не вийшов — запиши чому і йди далі)
1. Опиши середовище: ОС, `python3 --version`, CPU (`nproc`), RAM, GPU (`nvidia-smi`, якщо є), вільне місце на диску, чи є доступ в інтернет (pypi.org, download.blender.org, github.com).
2. **Blender.** Спробуй по черзі, перший спосіб, що спрацював, — далі:
   - a) `pip install bpy==4.5.*` (потрібен Python 3.11; якщо його немає — спробуй `uv python install 3.11` або `apt`), перевір `python -c "import bpy, mathutils; print(bpy.app.version_string)"`;
   - b) завантаж Blender 4.5 LTS для Linux x64 з `https://download.blender.org/release/Blender4.5/` (tar.xz), розпакуй, `./blender --background --version`.
   Запиши час встановлення і розмір.
3. **Перевірки.** Запусти по одній (запиши результат, рядок `RESULT` і час):
   - `blender --background --python world/build/check_components.py`
   - `blender --background --python world/build/check_trucks.py`
   - `blender --background --python world/build/check_controls.py`
   - потім `python world/build/check_all.py` (якщо він знаходить blender: подивись у файлі, як він шукає шлях до Blender; якщо шлях захардкоджений під Windows — НЕ змінюй файл, просто запиши, а для запуску використай змінну середовища чи symlink, якщо це можливо без правки коду).
   Якщо `pip bpy`: чек-скрипти запускай як `python world/build/check_X.py` і запиши, чи це працює.
4. **Рендер на CPU.** Створи скрипт **лише** в `delegation/cloud/probe/render_truck.py`, який будує фуру `kit/trucks.py` (`tr.rig(0.0, load=0.9)` і `tr.rig(44.5, variant=1)` на 8 м поруч), Cycles CPU, 32 семпли, 960×540, і зберігає `delegation/cloud/probe/truck.png`. Приклад побудови сцени й матеріалів — `world/kit/common.py` (`reset_scene`, `setup_render`, `setup_sky`, `mesh_from_arrays`, `mat_painted`, `camera`, `render`). Запиши час рендеру.
5. **Git.** Закоміть лише `delegation/cloud/probe/*` і звіт у свою гілку `claude/...` і запуш. У `master` не пуш.

## Результат
`delegation/cloud/C0_report.md`: таблиця «крок — вийшло / ні — час — примітка», точні команди, що спрацювали, повний вивід `RESULT` кожної перевірки, і розділ «Що я можу і не можу робити в цьому проєкті» (Blender так/ні, рендер так/ні і як швидко, GPU, доступ до інтернету, обмеження розміру репо/LFS). Без прикрас: якщо щось не працює — так і пиши.

Правила: не змінюй файли поза `delegation/cloud/`; не реєструйся ніде і не вводь ключів; `.env` не читай і не друкуй; не чіпай `inbox/records/`.
