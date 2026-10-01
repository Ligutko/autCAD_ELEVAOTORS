# Хмарний Claude Code: як працювати з цим репозиторієм

Проба C0 (2026-10-01, `C0_report.md`): Ubuntu, 4 ядра, 15 ГБ RAM, без GPU; Blender лише як pip-модуль `bpy` (download.blender.org закритий проксі). Усі 27 перевірок проходять, `check_all` ~8 хв.

## Підготовка (на початку кожної сесії, контейнер одноразовий)

```bash
python3.11 -m venv /tmp/bpyenv && /tmp/bpyenv/bin/pip install -q 'bpy==4.5.*'
export CLOUD_PY=/tmp/bpyenv/bin/python
export BLENDER="$PWD/world/build/cloud_blender"
```

## Запуск

- одна перевірка: `$BLENDER --background --python world/build/check_X.py`
- усі перед комітом: `$CLOUD_PY world/build/check_all.py --jobs 4` (має бути `27/27 checks pass` або більше)
- рендер: лише Cycles CPU; для перегляду 960×540, 32 семпли.

## Правила для задач

- Працюй тільки в межах файлів, названих у брифі; пуш лише у свою гілку `claude/*`, ніколи в `master`.
- Перед комітом прочитай рядок `N/N checks pass`; якщо щось падає — не послаблюй допуски, виправ геометрію або вимір.
- Кожна нова перевірка має зламаний варіант, що падає на своєму правилі.
- Кадри з результатом клади в `delegation/cloud/<задача>/` (960×540 PNG), щоб їх можна було переглянути.
- Не читай і не друкуй `.env`, не змінюй `inbox/records/`, не пиши `cited`.
