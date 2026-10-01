# Звіт C0: чи працює конвеєр у хмарі (проба)

Дата: 2026-10-01. Гілка: `claude/modest-mccarthy-epkh4h`. Код моделі, `world/`, `.env` і `inbox/records/` не чіпав. Нові файли лише в `delegation/cloud/`.

## Підсумок

Blender у цьому середовищі працює через `pip install bpy==4.5.*`. Усі 27 перевірок `world/build/check_*.py` проходять (`27/27 checks pass`). Рендер Cycles на CPU: 960×540, 32 семпли, 14,7 с. GPU немає. `download.blender.org` заблокований проксі (403), тож шлях b) недоступний.

## Таблиця кроків

| Крок | Вийшло? | Час | Примітка |
|---|---|---|---|
| 1. Опис середовища | так | — | див. нижче |
| 2a. `pip install bpy==4.5.*` (Python 3.11) | **так** | 29 с | поставився `bpy 4.5.14 LTS`; venv 950 МБ, з них пакет `bpy` 800 МБ |
| 2b. Blender tar.xz з download.blender.org | **ні** | — | `CONNECT tunnel failed, response 403` (egress-проксі, політика організації). Не потрібен, бо 2a спрацював |
| 3.1 `check_components.py` | так, **з обгорткою** | 15,6 с | «як є» падає, див. «Нюанс mathutils» |
| 3.2 `check_trucks.py` | так, без обгортки | 1,3 с | `RESULT ALL PASS` |
| 3.3 `check_controls.py` | так, без обгортки | 39,2 с | `RESULT ALL PASS` |
| 3.4 `check_all.py` (27 перевірок, `--jobs 4`) | так, через `BLENDER=` | 461,7 с (7,7 хв) | `27/27 checks pass`, код виходу 0 |
| 4. Рендер фур на CPU | так | 15,5 с повністю, з них рендер 14,7 с | `delegation/cloud/probe/truck.png` |
| 5. Git: коміт і пуш у `claude/...` | див. кінець звіту | — | у `master` не пушив |

## Крок 1. Середовище

- ОС: Ubuntu 24.04.4 LTS, ядро Linux 6.18.44-fc-v50 (Firecracker-ВМ), користувач root.
- Python: `python3 --version` дає 3.11.15. Також є 3.10, 3.12, 3.13 у `/usr/bin`. Є `uv` у `/root/.local/bin`.
- CPU: `nproc` = 4.
- RAM: 15 ГБ усього, 13 ГБ вільно, swap немає.
- GPU: немає (`nvidia-smi: command not found`).
- Диск: корінь 252 ГБ, зайнято 9,6 ГБ. Фактичний ліміт на сесію вказують як ~29 ГБ вільно (`df`). Звичайний `df` тут оманливий.
- Інтернет іде через проксі з allowlist. Результати:
  - `pypi.org` — 200 (у тому числі завантаження колес; `files.pythonhosted.org` на голий корінь дає 404, але pip працює);
  - `github.com` і `api.github.com` — 200;
  - `download.blender.org` — **403, заблоковано**;
  - `mirrors.kernel.org` — недоступний (000), інші Linux-дзеркала не перевіряв.

## Крок 2. Blender

Команди, що спрацювали:

```bash
python3.11 -m venv <venv>
<venv>/bin/pip install 'bpy==4.5.*'          # 29 с, bpy-4.5.14, numpy-1.26.4
<venv>/bin/python -c "import bpy, mathutils; print(bpy.app.version_string)"   # 4.5.14 LTS
```

Версія збігається з тією, на якій ми працюємо у Windows (4.5 LTS), хоч патч-версію не порівнював.

## Нюанс mathutils (важливо для всіх перевірок)

У pip-збірці `mathutils` стає імпортованим **лише після `import bpy`**. `check_components.py` робить `from mathutils.bvhtree import BVHTree` у рядку 29 до будь-якого `import bpy`, тому запуск «як є» дає:

```
ModuleNotFoundError: No module named 'mathutils'
```

Решта перевірок спершу імпортують `kit.*`, а там `common.py` починається з `import bpy`, тому вони запускаються як є. Файл `check_components.py` я не змінював. Обхід:

```bash
python -c "import bpy, runpy; runpy.run_path('world/build/check_components.py', run_name='__main__')"
```

Пропозиція для основного репозиторію (не робив, бо заборонено): додати `import bpy  # noqa` перед `from mathutils...` у `check_components.py`.

## Нюанс check_all.py

`check_all.py` бере шлях до Blender зі змінної `BLENDER`, інакше використовує захардкоджений `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`. Він запускає `[BLENDER, "--background", "--python", path]`. З pip-`bpy` справжнього виконуваного файла немає, тому без правки коду я зробив у scratchpad (поза репозиторієм) shell-обгортку `blender`. Вона розбирає `--python X` і виконує `python -c "import bpy, runpy; ... runpy.run_path(X, run_name='__main__')"`. Запуск:

```bash
BLENDER=/шлях/до/обгортки/blender <venv>/bin/python world/build/check_all.py --jobs 4
```

Обгортка зроблена лише для проби і в репозиторій не потрапила. Якщо вона знадобиться, її можна покласти в `delegation/cloud/probe/` на вимогу.

## Повний вивід `RESULT` кожної перевірки (кроки 3.1–3.3)

- `check_components.py` (з обгорткою): 15 PASS, 0 FAIL, 15,6 с. Останні рядки:
  ```
  EXPECTED FAIL таблиця з порушеною монотонністю -> OK
  CASES 84 base + 6 broken, caught 6/6
  RESULT ALL PASS
  ```
- `check_trucks.py`: 7 PASS, 0 FAIL, 1,3 с, `RESULT ALL PASS`.
- `check_controls.py`: 42 PASS, 0 FAIL, 39,2 с, `RESULT ALL PASS`.

## Повний вивід `check_all.py`

Чотири паралельні процеси, сумарно 461,7 с (стіна). Рядок `RESULT ALL PASS` кожної перевірки враховано самим `check_all.py` (він вважає перевірку пройденою лише за такого рядка і коду виходу 0).

```
ALL PASS  check_aeration            30 cases     1.5 s
ALL PASS  check_aspiration          32 cases    17.9 s
ALL PASS  check_components          15 cases    14.8 s
ALL PASS  check_controls            42 cases    41.1 s
ALL PASS  check_design              17 cases     0.6 s  1 WARN
ALL PASS  check_distribution        11 cases     0.8 s
ALL PASS  check_drying              21 cases     4.5 s  1 WARN
ALL PASS  check_environment         39 cases    42.3 s
ALL PASS  check_foundation          30 cases     7.4 s  1 WARN
ALL PASS  check_gallery             29 cases     0.6 s
ALL PASS  check_gates                9 cases     2.2 s
ALL PASS  check_lighting            20 cases   244.3 s  1 WARN
ALL PASS  check_live                33 cases   167.6 s  1 WARN
ALL PASS  check_noria                4 cases     1.6 s
ALL PASS  check_operator_room        7 cases     1.1 s
ALL PASS  check_panel               15 cases     9.0 s  2 WARN
ALL PASS  check_people               4 cases     1.8 s
ALL PASS  check_process             35 cases     1.4 s  1 WARN
ALL PASS  check_receiving           39 cases     3.1 s  1 WARN
ALL PASS  check_routes              45 cases   408.6 s
ALL PASS  check_silo_interior       21 cases     1.5 s
ALL PASS  check_silo_roof           25 cases    68.8 s
ALL PASS  check_sim                 39 cases   234.8 s
ALL PASS  check_site_plan           35 cases     3.8 s
ALL PASS  check_tower               33 cases     0.8 s
ALL PASS  check_trucks               7 cases     1.4 s
ALL PASS  check_tunnel              57 cases     1.2 s

27/27 checks pass
```

Попередження (WARN) я не розбирав: це рядки `PASS ... WARN` з самих перевірок, вони не провали. Я не порівнював їх зі Windows-запуском.

Найдовші: `check_routes` 409 с, `check_lighting` 244 с, `check_sim` 235 с, `check_live` 168 с. Якщо на Windows вони йдуть швидше, то, ймовірно, через кількість ядер: у хмарі лише 4, а при `--jobs 4` вони ще й ділять їх між собою.

## Крок 4. Рендер

Скрипт: `delegation/cloud/probe/render_truck.py`. Запуск: `python delegation/cloud/probe/render_truck.py` (pip bpy). Він також має працювати як `blender --background --python ...`, але в такому вигляді я його не запускав.

- Сцена: `tr.rig(0.0, load=0.9)` (біла кабіна, повний кузов зерна) і `tr.rig(44.5, variant=1)` (червона кабіна, кузов піднятий на 44,5°) на 8 м одна від одної вздовж осі Y.
- Cycles, `device = CPU`, 32 семпли, 960×540, денойзінг і AgX з `common.setup_render`, небо з `common.setup_sky`, асфальт `common.mat_asphalt`.
- Час: побудова сцени 0,2 с, рендер 14,7 с, разом із запуском Python 15,5 с.
- Файл `delegation/cloud/probe/truck.png`: 493 КБ. На картинці видно обидва тягачі, піднятий кузов, зерно у нижчому кузові, колеса на асфальті. Зображення переглянув, артефактів, що ламають кадр, не помітив.
- Матеріали в скрипті мої, прості: колір за назвою частини меша (`tractor_cab`, `*_tyres`, `trailer_grain` тощо). Це не еталон вигляду проєкту.
- Під час написання скрипта була одна помилка: `mesh_from_arrays` очікує `faces` як numpy-масив, а не список списків. Виправлено в моєму скрипті, `common.py` не чіпав.

## Що я можу і не можу робити в цьому проєкті

**Можу:**
- Blender: **так**, `bpy 4.5.14 LTS` через pip (29 с, ~800 МБ пакет) без збирання. Усі `check_*.py` і `check_all.py` проходять (27/27).
- Рендер: **так**, Cycles CPU. Проба 960×540 / 32 семпли = 15 с для двох фур. Повні сцени майданчика будуть значно довшими, цього я не міряв.
- Редагувати Python у `world/`, запускати `check_all.py` перед комітом (близько 8 хв на 4 ядрах; для швидшого циклу можна `--only`).
- Працювати з git/GitHub: читання і пуш у `claude/*` працюють.

**Не можу / обмеження:**
- GPU немає: Cycles лише CPU, 4 ядра, 15 ГБ RAM. Важкі кадри (1920×1080, 128+ семплів, великі сцени) будуть повільними.
- `download.blender.org` заблокований (403), тож офіційний tar.xz Blender не завантажити. Єдиний шлях зараз це pip `bpy`. Відмінності від десктопного Blender: нема `--background` CLI; запуск лише як модуль Python (потрібна обгортка для `check_all.py`, див. вище); не перевіряв `bpy.ops` на кшталт UI-операцій і GUI-скрипти (`viewport_probe.py`, `live_*`).
- Не перевіряв: Windows-специфічні скрипти (`render_awake.ps1`), `world/panel/` і `world/sim/` у браузері, FFmpeg/відео (`reel.py`), якщо він потрібен.
- Інтернет через проксі з allowlist: pypi.org і github.com є, інші хости можуть бути закриті (приклад: blender.org). Це важливо для агента-дослідника з веб-пошуком, цього я не перевіряв.
- Середовище одноразове: контейнер знищується після сесії, `pip install bpy` доведеться повторювати (≈30 с) на кожну нову сесію. Це можна автоматизувати SessionStart-хуком.

**Розмір репозиторію і LFS:**
- `.git` ≈ 583 МБ (pack 581 МБ), робоча копія без `.git` ≈ 712 МБ. Клон і checkout у хмарі пройшли без проблем.
- `.gitattributes` немає, LFS не використовується (git-lfs 3.4.1 установлений, але файли в LFS не лежать).
- Лімітів розміру репозиторію в середовищі я не зустрів. Для великого вихідного артефакта (PNG/MP4) варто пам'ятати, що репозиторій уже ~0,6 ГБ.
- Свій `truck.png` (493 КБ) я закомітив, щоб він був у звіті. Якщо такі файли не потрібні в git, видаліть його.
