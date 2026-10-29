"""Fixture consumer adapter: Python AST identity plus explicit dependency declarations."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

test_file, test_id = sys.argv[1:3]
source = Path(test_file).read_text(encoding="utf-8")
selected_file, separator, function_name = test_id.partition("::")
if not separator or selected_file != test_file:
    raise SystemExit("test ID does not select the requested file")
tree = ast.parse(source)
matches = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
           and node.name == function_name]
if len(matches) != 1:
    raise SystemExit("stable test ID did not resolve exactly once")
canonical = ast.dump(matches[0], annotate_fields=True, include_attributes=False)
dependencies = [{"kind": match.group(1), "path": match.group(2)} for match in re.finditer(
    r"^# cgspec-dependency (helper|fixture|import|snapshot|config) ([^\s]+)$", source, re.MULTILINE)]
print(json.dumps({
    "schema": 1,
    "test_id": test_id,
    "semantic_fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    "closure_complete": True,
    "dependencies": dependencies,
}))
