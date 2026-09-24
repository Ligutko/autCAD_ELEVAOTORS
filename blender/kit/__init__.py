"""Кіт елеватора: іменовані деталі в метрах.

Світ (`blender/assemble_site.py`) ставить лише деталі з REGISTRY.
Немає типу в реєстрі — збірка падає з назвою відсутньої деталі.
"""

from . import noria_n100, silo_msvu_220

REGISTRY = {
    silo_msvu_220.TYPE: silo_msvu_220,
    noria_n100.TYPE: noria_n100,
}
