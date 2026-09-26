---
type: node
status: done
updated: 2026-09-26
code: world/kit/distribution.py
build: world/build/k2_tower.py
out: world/out/k2_tower/
tags: [node, distribution]
---
# Distribution (розподіл під головою норії)

Повернутись: [[00 Handoff]]

За `research/tunnel_k4.md` «Розподіл під головою норії» (SITE.json `distribution`).
- Вихід голови → збірна коробка → ввід трійний 45° з трьома засувками ТЗА-300 і моторами (H5, H6).
- H6 має ще ввід двійний обходу T11 з двома засувками.
- Спуски □300: H5 → T8 / T10 / T11; H6 → T12 / T14 / T15. Похили 47–88°.
- Вихід голови в моделі збігається з кресленням до 15 мм.

Перевірка: `world/build/check_distribution.py`; що кінці спусків лягають на конвеєри, перевіряє `check_gallery.py`.
Не тут: вводи й 7 засувок 1 черги в приймальній вежі (блок F).
