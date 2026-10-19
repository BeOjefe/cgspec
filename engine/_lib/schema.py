"""A small JSON Schema subset validator (draft-07 keywords CGSpec uses), stdlib only.

Supported: type, enum, const, required, properties, additionalProperties (bool or schema),
items, minItems, minLength, pattern, minimum, maximum, anyOf, $ref to "#/definitions/...".
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate(value: Any, schema: dict, root: dict | None = None, at: str = "$") -> list[str]:
    """Return a list of human-readable errors; empty means valid."""
    root = root or schema
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/definitions/"):
            return [f"{at}: unsupported $ref {ref}"]
        return validate(value, root["definitions"][ref.split("/")[-1]], root, at)

    errors: list[str] = []
    if "anyOf" in schema:
        if all(validate(value, option, root, at) for option in schema["anyOf"]):
            errors.append(f"{at}: matches none of the allowed shapes")
        return errors

    expected = schema.get("type")
    if expected is not None:
        names = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, n) for n in names):
            return [f"{at}: expected {'/'.join(names)}, got {type(value).__name__}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{at}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{at}: {value!r} not in {schema['enum']}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{at}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{at}: {value!r} does not match {schema['pattern']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{at}: below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{at}: above maximum {schema['maximum']}")

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{at}: missing required key '{key}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for key, item in value.items():
            if key in props:
                errors += validate(item, props[key], root, f"{at}.{key}")
            elif extra is False:
                errors.append(f"{at}: unexpected key '{key}'")
            elif isinstance(extra, dict):
                errors += validate(item, extra, root, f"{at}.{key}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{at}: needs at least {schema['minItems']} items")
        if "items" in schema:
            for index, item in enumerate(value):
                errors += validate(item, schema["items"], root, f"{at}[{index}]")
    return errors


def validate_named(value: Any, name: str) -> list[str]:
    return validate(value, load_schema(name))
