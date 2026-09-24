---
type: architecture
updated: 2026-09-24
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
    silo_interior.py  K5 нутро силоса          → [[K5 Silo Interior]]
    cameras.py        D1 рухи камери           → [[D1 D3 Cameras and Reels]]
  build/              сцени: k1_silo, k2_tower, k2b_noria, k5_interior, site (assemble()), reel
  reels/*.json        специфікації роликів
  out/<вузол>/        кадри, README (параметр — значення — джерело), measure.json
```

## Принципи
- Сітки будуються numpy → `mesh_from_arrays` (швидко, мільйони вершин).
- Однакові вузли — екземпляри колекції (6 силосів = 1 сітка).
- Знімні частини (кришки голови/башмака) — окремі об'єкти для розрізів.
- Розріз: `cut=(nx, ny)` у `silo.build` / `silo_interior.build` прибирає половину до камери, великі грані й n-кутники ріжуться точно.
- Підписи: `common.labels()` → колекція `LABELS_<id>`; `face_labels(cam)` ставить їх на екрані без перетинів і ховає закриті; `render_with_labels` рендерить їх другим проходом поверх кадру.
- Рендер: Cycles, AgX, небо Nishita + сонце; `--quick` для чернеток.
