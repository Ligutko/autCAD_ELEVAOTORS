---
type: node
status: done
updated: 2026-09-24
code: world/kit/cameras.py, world/build/reel.py
specs: world/reels/
out: world/out/reels/
tags: [node, camera, reels]
---
# D1 D3 Cameras and Reels

Повернутись: [[00 Handoff]]

Рухи: `orbit`, `dolly`, `push_in`, `crane`, `walk` (перша особа 1.7 м, 1.2 м/с, легке похитування), плавний розгін. Ролик з JSON: стани `clay` / `wire` / `final`, гачок і підписи кирилицею (PIL), склейка ffmpeg у MP4, формати 9:16 / 16:9 / 1:1, `--preview` (½ розміру, 12 к/с, 8 семплів).
Сцени в `reel.py` → `SCENES`: поки лише `site`; додати `k5`, `noria` (виділити `assemble()` у їхніх скриптах).
Перший ролик: `world/reels/reel_01_site.json`.
