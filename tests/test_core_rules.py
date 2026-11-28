"""design.md 규칙: app/core는 streamlit, firebase_admin을 import하지 않는다."""

import ast
from pathlib import Path

import pytest

CORE_DIR = Path(__file__).resolve().parent.parent / "app" / "core"
FORBIDDEN = {"streamlit", "firebase_admin"}


@pytest.mark.parametrize("path", sorted(CORE_DIR.glob("*.py")), ids=lambda p: p.name)
def test_core_does_not_import_streamlit_or_firebase(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & FORBIDDEN), f"{path.name}에서 금지된 import: {imported & FORBIDDEN}"
