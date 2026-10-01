# Завдання C2 для хмарного Claude Code: привід скребкового конвеєра ТЦС — насадний мотор-редуктор

Середовище і запуск: `delegation/cloud/README.md`. Пуш лише у свою гілку `claude/*`. Мова звіту: українська. Інтернету немає, усі джерела в репозиторії.

## Навіщо
10 ланцюгових конвеєрів У13-ТЦС-320 (кВт у `world/site/SITE.json` → `equipment.items`, `model: У13-ТЦС-320`: 11, 15, 18,5). Їхній привід зараз — коробка + циліндр: `world/kit/gallery.py` `conveyor()` (галереї T8/T12/T15 і естакади T7/T10/T11/T14) і `world/kit/tunnel.py` (рядки ~215–220, тунельні конвеєри). Людина проходить повз на 0,3–1 м.

## Джерела (у `research/design/components/sources/`)
`SEW_9PD0008_KA_dimensions.pdf` (SEW-EURODRIVE, габаритні креслення насадних конічно-циліндричних мотор-редукторів KA), `Bonvario_B-KA_torque_arm.pdf` (реактивна тяга), `Cimbria_RM_datasheet.pdf` і `Skandia_KTIF_pds.pdf` (ланцюгові конвеєри: як стоїть привід). Двигун — готовий `iec_motor(kw)` у `world/kit/components.py`.

## Кроки (кожен — окремий коміт)
1. **Дані** → `world/kit/data/gearmotor_ka.json` (формат `{"v","src","basis","note"}`, мм): один типорозмір KA під 11–18,5 кВт (напр. KA87 / KA97; обґрунтуй вибір), габарит корпусу, порожнистий вал Ø, відстань від осі виходу до осі двигуна, фланець двигуна, реактивна тяга; з Cimbria / Skandia — з якого боку і як привід стоїть на головній секції. Чого нема — `NOT_FOUND`.
2. **Компонент** `shaft_gearmotor(kw)` у `components.py` (numpy, як `iec_motor`): корпус редуктора (не коробка: циліндрична частина + конічна камера, кришки, ребра), порожнистий вихід з кришкою, фланцевий двигун (`iec_motor` у фланцевому виконанні або еквівалент), реактивна тяга з опорою. Локальну систему опиши в docstring.
3. **Перевірки** в `world/build/check_components.py`: габарити = дані ±5 мм; осі як у кресленні; двигун торкається фланця (0 ± 2 мм); тяга кріпиться до корпусу; **зламаний варіант на кожне правило**, що падає саме на ньому. Допуски не послаблюй.
4. **Заміна** в `gallery.conveyor()` і в `tunnel.py`: привід на валу головної зірочки, з боку проходу, тяга до кожуха. Ключі частин `drive` / `motor` залиш (їх читають сцени, `routes.py`, `live.py`, `check_controls`). **Увага:** `gallery.estop_place` і `check_controls` ставлять аварійний пост поруч із приводом — після заміни вони мають пройти без зміни допусків; якщо пост не влазить, розберись чому й опиши.

## Готово, коли
`$CLOUD_PY world/build/check_all.py --jobs 4` → `N/N checks pass` (рядок у звіті); кадри 960×540, Cycles CPU, 32 семпли: `delegation/cloud/C2/drive.png` (привід крупно) і `delegation/cloud/C2/gallery.png` (привід на галереї з аварійним постом поруч); звіт `delegation/cloud/C2_report.md`.

## Межі
Змінюй лише: `world/kit/components.py`, `world/kit/data/gearmotor_ka.json`, `world/kit/gallery.py` (лише `conveyor()`), `world/kit/tunnel.py` (лише привід конвеєра), `world/build/check_components.py`, `delegation/cloud/`. Не чіпай `receiving.py`, `trucks.py`, `figures.py`, `sim/`, `live.py`: над ними зараз працює інша сесія.
