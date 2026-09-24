# Відкриті 3D/CAD-моделі вузлів

Дата: 2026-09-24
Жодна модель нижче **не завантажена**: з цього контейнера відкриваються лише GitHub, GitLab і PyPI. Сайти CAD-бібліотек заблоковані (див. `BLOCKED.md`). Посилання знайдено через пошук. Ліцензію кожної моделі перевірити на її сторінці перед використанням.

Правило для проєкту: у сцену беремо лише моделі, ліцензія яких дозволяє перевикористання. Каталоги виробників (TraceParts, 3Dfindit, SKF PARTcommunity, 3D ContentCentral) зазвичай дозволяють вбудовувати модель у власний проєкт, але забороняють її перепродавати. Моделі GrabCAD належать авторам: за умовами сайту їх не можна перепубліковувати, а дозвіл на використання в роликах треба перевіряти окремо.

## Норія цілком

| Що | URL | Формат | Ліцензія | Звідси завантажується? |
|---|---|---|---|---|
| Grain Elevator (GrabCAD) | https://grabcad.com/library/grain-elevator-1 | за сторінкою | умови GrabCAD, автор | ні, grabcad.com заблоковано |
| Bucket Elevator (Elevatör) | https://grabcad.com/library/bucket-elevator-elevator-1 | за сторінкою | умови GrabCAD | ні |
| Bucket Elevator | https://grabcad.com/library/bucket-elevator-15 | за сторінкою | умови GrabCAD | ні |
| Bucket Elevator (файли) | https://grabcad.com/library/bucket-elevator-32/files | за сторінкою | умови GrabCAD | ні |
| Добірка за тегом | https://grabcad.com/library/tag/bucket%20elevator | — | — | ні |
| Bucket elevator (TraceParts) | https://www.traceparts.com/en/product/bucket-elevator?Product=10-24092010-065147 | STEP, IGES, DWG, SOLIDWORKS та ін. | умови TraceParts, потрібна реєстрація | ні |
| Bucket Elevator (3DCADBrowser) | https://www.3dcadbrowser.com/3d-model/bucket-elevator | різні | комерційний сайт, перевірити | ні |
| Bucket elevator with silo (Bibliocad) | https://www.bibliocad.com/en/library/bucket-elevator_54806/ | DWG, 1.77 MB | умови Bibliocad | ні |
| Bucket-Elevator-CAD-Model-Development (GitHub) | https://github.com/rahulperumal25/Bucket-Elevator-CAD-Model-Development | AutoCAD / SolidWorks | **файлу ліцензії немає, тобто всі права в автора. Не використовувати** | так, але не брати |

Ланцюгові норії (GrabCAD «Bucket Elevator - Chain Type», «Chain Bucket Elevator») нам не підходять: у нас стрічкова норія.

## Ковші і норійні болти

| Що | URL | Формат | Ліцензія | Завантаження |
|---|---|---|---|---|
| Норійні болти (Elevator Bucket Screws) | https://www.3dfindit.com/en/keywords/elevator | STEP та ін. | каталог 3Dfindit (CADENAS), реєстрація | ні |
| Ковші 4B, Tapco, Maxi-Lift | не знайдено | — | — | — |

Готової відкритої моделі ковша Tapco чи 4B не знайшов. Ковш простіше будувати параметрично за таблицею `PARTS_DIMENSIONS.md`, розділ A1.

## Підшипникові корпуси

| Що | URL | Формат | Ліцензія | Завантаження |
|---|---|---|---|---|
| SKF SNL 2, 3, 5, 6 (офіційний портал SKF на PARTcommunity) | https://skf.partcommunity.com/3d-cad-models/?info=skf%2Fbearings_units_and_housings%2Fbearing_housings%2Fsplit_plummer_block_housings_-_se_and_snl_2356%2Fapc_hc_001.prj | STEP, IGES, нативні CAD | умови SKF / CADENAS, реєстрація | ні |
| SKF SNL на 3Dfindit | https://www.3dfindit.com/en/cad-bim-library/manufacturer/skf/bearings-units-and-housings/bearing-housings/split-plummer-block-housingsse-and-snl-2-3-5-and-6-series | те саме | те саме | ні |
| SNL plummer block SKF (GrabCAD) | https://grabcad.com/library/snl-plummer-block-skf-1 | за сторінкою | умови GrabCAD | ні |
| SKF на 3D ContentCentral | https://www.3dcontentcentral.com/parts/supplier/SKF.aspx | SOLIDWORKS, STEP | умови 3D ContentCentral | ні |
| Timken UCP211 | https://cad.timken.com/item/u-series---pillow-block-mounted-bearings--ucp-200-/ucp-pillow-block-units/ucp211 | STEP, DWG | умови Timken | ні |
| AMI UCP211 | https://catalog.amibearings.com/item/set-screw-locking/set-screw-locking-pillow-block-unit-ucp200-series/ucp211 | STEP, DWG | умови AMI | ні |
| NSK SNN (TraceParts) | https://www.traceparts.com/en/product/nsk-nsk-plummer-blocks-snn-serie?Product=10-16102013-085792 | STEP та ін. | TraceParts | ні |

Таблиці розмірів SNL і UCP211 вже є в `research/raw/bearings/`. Корпус SNL 520-617 можна будувати параметрично за ними.

## Мотор і редуктор

| Що | URL | Формат | Ліцензія | Завантаження |
|---|---|---|---|---|
| 180L B3 Right IEC electric motor (CGTrader) | https://www.cgtrader.com/3d-models/industrial/industrial-machine/180l-b3-right-iec-electric-motor-3d-cad-model | за сторінкою | ліцензія CGTrader (Royalty Free або Editorial), найімовірніше платна | ні |
| Редуктори NORD, SEW, Bonfiglioli, Dodge | конфігуратори на сайтах виробників | STEP | умови виробника, реєстрація | ні |

## Параметричні бібліотеки, доступні звідси

| Що | Звідки | Ліцензія | Що містить | Стан |
|---|---|---|---|---|
| bd_warehouse 0.3.0 (build123d) | `pip download bd_warehouse` з pypi.org | **Apache-2.0** | болти й гайки ISO/DIN (ISO 4014/4017, DIN 931), шайби, шпонки DIN 6885, кулькові й роликові підшипники, фланці, зірочки. Корпусних підшипників і норійних болтів DIN 15237 немає | таблиці hex_head, hex_nut, plain_washer, shaft_key, countersunk скопійовано в `research/raw/bolts/bd_warehouse_0.3.0/` разом з LICENSE |
| FreeCAD-library | https://github.com/FreeCAD/FreeCAD-library | за репозиторієм (CC-BY 3.0, перевірити) | загальні деталі; корпусних вузлів і норій пошук не знайшов | не завантажувалось |

Для анкерів (кейс 6) і болтів фланців норії таблиць bd_warehouse достатньо, щоб будувати болти в Blender з реальними розмірами головки й гайки.

## Висновок

Відкритої моделі стрічкової норії з вільною ліцензією не знайшов. Найкращі кандидати на готові STEP — каталоги виробників: SKF SNL, Timken або AMI UCP211, TraceParts. Їх треба завантажити з машини без проксі, перевірити умови і покласти в `research/raw/cad/`. Ковш, барабани, трубу, голову й башмак краще лишити параметричними в `world/kit/`: числа для них зібрано в `PARTS_DIMENSIONS.md`.
