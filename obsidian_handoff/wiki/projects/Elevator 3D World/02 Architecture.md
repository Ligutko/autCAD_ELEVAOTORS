---
type: architecture
updated: 2026-09-28
tags: [code, blender]
---
# 02 Architecture

Повернутись: [[00 Handoff]]

```
world/
  site/SITE.json      генплан: позиції, відмітки (метри, осі: X уздовж рядів, Y на північ, Z від ±0.000, початок — вісь норії H6)
  kit/                вузли: функція будує вузол у метрах, повертає частини і measure
    common.py         numpy-меші, PBR-матеріали (оцинковка, бетон, ґрунт), небо Nishita, камера, підписи, розріз cut_mesh, render_with_labels
    steel.py          профілі (SHS, кутник, двотавр, швелер), member(), грати, огорожа, сходи (EN ISO 14122)
    silo_msvu220.py   K1 силос зовні          → [[K1 Silo MSVU220]]
    noria_tower.py    K2 вежа                  → [[K2 Noria Tower]]
    noria_n100.py     K2b норія детально       → [[K2b Noria N100]]
    gallery.py        K3 естакади, міст, конвеєр → [[K3 Galleries]]
    distribution.py   розподіл під головою норії → [[Distribution]]
    tunnel.py         K4 тунелі, ТЛ-50К, засувки → [[K4 Tunnels]]
    aspiration.py     E бункери пилу, установки, повітроводи (WIP) → [[E Aspiration]]
    silo_interior.py  K5 нутро силоса          → [[K5 Silo Interior]]
    cameras.py        D1 рухи камери           → [[D1 D3 Cameras and Reels]]
    foundation.py     фундамент-кільце, підошва, анкери, земля −0.45 (ground_z)
    receiving.py      існуючий блок H1–H4 спрощено, яма, очисна вежа, Ш1, стики T7/T10
    process.py        граф процесу (чистий Python): маршрути, потік, засувки, пуск/зупинка, вузьке місце
    drying.py         сушарка в будівлі «4», T3, T5, спуски (шар designed)
    site_plan.py      генплан руху: смуги, ваги, АПК, КПП, КТП, пожежне кільце, гідранти; стрічки доріг
    environment.py    W1: земля з дірками, двір, узбіччя, огорожа й ворота, відмостки
    photometry.py     W1: читання IES LM-63, I(C, γ), потік
    lighting.py       W1: щогли й прожектори, освітленість з тінями, лампи Cycles з IES
    landscape.py      W1: дорога загального користування, під'їзди, поля, лісосмуги (екземпляри дерев)
    figures.py        W1: зерновози й люди для масштабу
  build/              сцени: k1_silo, k2_tower, k2b_noria, k4_tunnel, k5_interior, site (assemble()), reel
                      перевірки (17): check_{noria,tower,tunnel,distribution,gallery,aspiration,aeration,silo_interior,silo_roof,
                      foundation,receiving,process,design,drying,site_plan,environment,lighting}; check_all.py запускає всі
                      render_awake.ps1 — довгий рендер без сну ПК; site.py -- --night — нічні кадри
  reels/*.json        специфікації роликів
  out/<вузол>/        кадри, README (параметр — значення — джерело), measure.json
```

## Принципи
- Сітки будуються numpy → `mesh_from_arrays` (швидко, мільйони вершин).
- Однакові вузли — екземпляри колекції (6 силосів = 1 сітка).
- Знімні частини (кришки голови/башмака) — окремі об'єкти для розрізів.
- Розріз: `cut=(nx, ny)` у `silo.build` / `silo_interior.build` прибирає половину до камери, великі грані й n-кутники ріжуться точно.
- Підписи: `common.labels()` → колекція `LABELS_<id>`; `face_labels(cam)` ставить їх на екрані без перетинів і ховає закриті; `render_with_labels` рендерить їх другим проходом поверх кадру.
- Рендер: Cycles, AgX, небо Nishita + сонце; `--quick` для чернеток (у `world/out/site/w1_draft/`, не поверх фіналів); `--night` — прожектори з IES.
- Шари даних у SITE.json: `drawn` (креслення), `existing` (існуючий блок), `designed` (наш проєкт із записками `research/design/*.md`).
- Перевірки `check_*.py`: геометрія з кіту порівнюється з кресленням і специфікацією; у кожній є навмисно зламаний варіант, який мусить впасти. Усі мають пройти до коміту.
