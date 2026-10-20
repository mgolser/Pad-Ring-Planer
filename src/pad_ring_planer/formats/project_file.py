"""Project files (JSON)."""

import json
from pathlib import Path

from ..model.project import Project


def load(path):
    """Read a project file. Raises ``OSError`` or ``ValueError``."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "sides" not in data:
        raise ValueError("not a pad ring file")
    return Project.from_dict(data)


def save(project, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)
