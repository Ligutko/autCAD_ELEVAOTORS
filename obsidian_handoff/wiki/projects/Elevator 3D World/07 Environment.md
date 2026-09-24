---
type: environment
updated: 2026-09-24
tags: [cloud, network, render]
---
# 07 Environment

Повернутись: [[00 Handoff]]

- Хмарний контейнер Claude Code, Linux, 4 ядра, без GPU. Python 3.11.
- Blender: `pip install bpy==4.5.*` (модуль ~370 МБ; тимчасовий контейнер — ставити заново в новій сесії). Також `pillow numpy imageio-ffmpeg`.
- ffmpeg з pip (`imageio_ffmpeg.get_ffmpeg_exe()`), без drawtext — текст малюємо PIL.
- Шрифт з кирилицею: `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`.
- Мережа: відкриті pypi, github, raw.githubusercontent. Закриті: polyhaven, ambientcg, instagram, youtube, tiktok, більшість сайтів виробників і CAD-бібліотек (`research/BLOCKED.md`). Матеріали тому процедурні.
- Відео від користувача приходять файлами-вкладеннями; розбір — ffmpeg по 2 кадри/с, контактні аркуші, перегляд кадрів.
- Рендер: чернетка 960 px 24–32 семпли ~20–90 с; фінал 1920 px 128–160 семплів 5–28 хв на кадр.
- Гілка `claude/nice-noether-0p9c8r`, репо `ligutko/autcad_elevaotors`.
