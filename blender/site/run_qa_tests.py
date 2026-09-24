"""Перевірка воріт якості збирача (SLICE-6).

Чисті SITE мають дати SITE_PASS, кожен `tests/broken_*.json` — SITE_FAIL
з проблемою, яка відповідає його `expect_fail`. Рендер вимкнено.

Запуск:
    python blender/site/run_qa_tests.py                      # модуль bpy 4.5 у цьому python
    python blender/site/run_qa_tests.py --blender blender    # через blender --background
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSEMBLER = HERE.parent / "assemble_site.py"

# Слово, яке має бути в тексті проблеми, щоб FAIL рахувався «за правильну причину».
EXPECT = {
    "broken_underground.json": "нижче землі",
    "broken_overlap.json": "зазор",
    "broken_unknown_type.json": "немає деталі кіта",
    "broken_param_override.json": "не змінює розміри",
    "broken_duplicate_id.json": "повторюється",
    "broken_noria_in_silo.json": "заходить у силос",
}


def run(site: Path, out: Path, blender: str | None) -> tuple[int, dict]:
    if blender:
        cmd = [blender, "--background", "--factory-startup", "--python", str(ASSEMBLER), "--", str(site)]
    else:
        cmd = [sys.executable, str(ASSEMBLER), str(site)]
    cmd += ["--no-render", "--out", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    qa_path = out / "qa.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8")) if qa_path.exists() else {}
    return proc.returncode, qa


def main() -> int:
    blender = None
    if "--blender" in sys.argv:
        blender = sys.argv[sys.argv.index("--blender") + 1]
    rows = []
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for site in sorted(HERE.glob("SITE_*.json")):
            code, qa = run(site, tmp / site.stem, blender)
            good = code == 0 and qa.get("pass") is True
            ok &= good
            rows.append((site.name, "PASS очікується", "PASS" if code == 0 else "FAIL", good, qa.get("problems", [])))
        for site in sorted((HERE / "tests").glob("broken_*.json")):
            code, qa = run(site, tmp / site.stem, blender)
            problems = qa.get("problems", [])
            word = EXPECT.get(site.name, "")
            good = code == 2 and qa.get("pass") is False and any(word in p for p in problems)
            ok &= good
            rows.append((site.name, f"FAIL «{word}»", "PASS" if code == 0 else "FAIL", good, problems))
    for name, expected, got, good, problems in rows:
        print(f"{'OK ' if good else 'BAD'} {name:34s} очікується {expected:28s} отримано {got}  {problems[:2]}")
    print("QA_TESTS_PASS" if ok else "QA_TESTS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
