---
type: handoff
updated: 2026-09-24
repo: ligutko/autcad_elevaotors
branch: claude/nice-noether-0p9c8r
tags: [handoff, start-here]
---
# 00 Handoff — для наступного агента

Повернутись: [[Elevator 3D World MOC]]

## Що це
Будуємо реальний комплекс (6 силосів МСВУ 220, дві норійні вежі, естакади, тунелі) з `Технологія 06.06.24.pdf` у Blender: 1:1, фотореально, з можливістю зайти всередину, показати вузол у розрізі з підписами приладів і зняти ролик «аварія → причина → як треба». Деталі: [[01 Goal and Vision]].

## Стан на 2026-09-24
| Готово | Де |
|---|---|
| Генплан з PDF у числах | `world/site/SITE.json` → [[Real Object]] |
| Силос зовні (K1) | [[K1 Silo MSVU220]] |
| Норійна вежа (K2) і детальна норія (K2b) | [[K2 Noria Tower]], [[K2b Noria N100]] |
| Естакади і міст (K3) | [[K3 Galleries]] |
| Нутро силоса + розрізи (K5) | [[K5 Silo Interior]] |
| Камери і збирач роликів (D1, D3) | [[D1 D3 Cameras and Reels]] |
| Дослідження розмірів | [[Research Sources]] |

Не зроблено: оточення W1 (найбільший стрибок реалізму), тунелі K4, сценарії кейсів, приймальна частина K6, анімація D2, запуск на ПК E1. Порядок — [[03 Roadmap]].

## Як запустити (хмара або ПК)
```
pip install bpy==4.5.*            # Blender 4.5 як модуль Python (у хмарі вже стоїть не завжди — див. [[07 Environment]])
python world/build/k1_silo.py --quick
python world/build/k2b_noria.py --quick
python world/build/k5_interior.py --quick
python world/build/site.py --quick
blender --python world/build/site.py -- --no-render     # відкрити сцену і літати (на ПК)
python world/build/reel.py world/reels/reel_01_site.json --preview
```
Кадри: `world/out/<вузол>/`, кожен має `README.md` (параметр — значення — джерело) і `measure.json`.

## Наступний крок
**W1 — оточення**: бетон і асфальт за PDF p.2, трава розсипом, поля і лісосмуги на горизонті, об'ємний туман, пресети часу доби і зими. Специфікація — `BUILD_SPEC.md`, розділ 3. Правило приймання кадру — [[Canon World]].

## Правила роботи (обов'язково)
1. Кожне число в коді з позначкою джерела: `PDF p.N`, `LUB`, `STD`, `research`, `EST`. Неправдоподібне заборонено. → [[01 Goal and Vision]]
2. «Готово» для вузла: товщини, болти, маточини, знімні кришки, підписи. → `BUILD_SPEC.md` §0.1
3. Кожен вузол: 3–4 контрольні кадри, подивитися їх очима, виправити, потім фінал.
4. Комітити і пушити в `claude/nice-noether-0p9c8r`; `.blend` і кадри роликів не комітити (є в `.gitignore`).
5. Спілкування з користувачем — українською, конкретно, без «рожевих окулярів».
6. Перед роботою прочитати [[05 Lessons and Pitfalls]].

## Ключові файли репозиторію
`VISION_3D_WORLD.md`, `BUILD_SPEC.md`, `PRODUCTION_PLAN.md`, `CANON_DETAIL.md`, `CANON_WORLD.md`, `FIELD_CASES.md`, `research/PARTS_DIMENSIONS.md`, `world/`.
Старі файли в корені (AutoCAD-скрипти, `config_*.json`) — попередній етап 2D; для 3D не використовувати, генплан у них неправильний.
