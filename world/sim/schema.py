"""A small JSON Schema validator for world/sim/STATE_SCHEMA.json: no dependencies (Blender's Python has no
jsonschema). Supports the keywords the contract uses: type (incl. lists), required, properties,
additionalProperties (bool or schema), enum, items, minimum, maximum, exclusiveMinimum."""

import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / "STATE_SCHEMA.json"
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t):
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    return isinstance(v, TYPES[t])


def errors(v, s, path="$"):
    out = []
    t = s.get("type")
    if t is not None:
        ts = t if isinstance(t, list) else [t]
        if not any(_is(v, x) for x in ts):
            return [f"{path}: {type(v).__name__} is not {t}"]
    if "enum" in s and v not in s["enum"]:
        out.append(f"{path}: {v!r} not in {s['enum']}")
    if _is(v, "number"):
        if "minimum" in s and v < s["minimum"]:
            out.append(f"{path}: {v} < {s['minimum']}")
        if "maximum" in s and v > s["maximum"]:
            out.append(f"{path}: {v} > {s['maximum']}")
        if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
            out.append(f"{path}: {v} <= {s['exclusiveMinimum']}")
    if isinstance(v, dict):
        props = s.get("properties", {})
        for k in s.get("required", []):
            if k not in v:
                out.append(f"{path}: missing {k!r}")
        extra = s.get("additionalProperties", True)
        for k, x in v.items():
            if k in props:
                out += errors(x, props[k], f"{path}.{k}")
            elif extra is False:
                out.append(f"{path}: unexpected {k!r}")
            elif isinstance(extra, dict):
                out += errors(x, extra, f"{path}.{k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            out += errors(x, s["items"], f"{path}[{i}]")
    return out


def validate(state, schema=None):
    return errors(state, schema or json.loads(SCHEMA.read_text(encoding="utf-8")))
