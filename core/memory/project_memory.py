# core/memory/project_memory.py
import json
import shutil
from pathlib import Path
from datetime import datetime
from core.interfaces.memory import Memory


class ProjectMemory(Memory):
    """
    Memoria permanente de un proyecto específico.
    Persistencia: memory/<project>/context.json
    Ver MEMORY.md §5.
    """

    def __init__(self, project: str, base_dir: str = "memory"):
        super().__init__(project)
        self.base_dir = Path(base_dir)
        self.project_dir = self.base_dir / project
        self.context_file = self.project_dir / "context.json"
        self._ensure_dirs()
        self._data = self._load_from_disk()

    def _ensure_dirs(self):
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def _load_from_disk(self) -> dict:
        if self.context_file.exists():
            with open(self.context_file, "r") as f:
                return json.load(f)
        return {}

    def _save_to_disk(self):
        with open(self.context_file, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def save(self, key: str, value) -> None:
        self._data[key] = value
        self._data["_updated_at"] = datetime.now().isoformat()
        self._save_to_disk()

    def load(self, key: str):
        return self._data.get(key)

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]
            self._save_to_disk()

    def clear(self) -> None:
        self._data = {}
        self._save_to_disk()

    def list_keys(self) -> list:
        return [k for k in self._data.keys() if not k.startswith("_")]

    def snapshot(self) -> dict:
        return {k: v for k, v in self._data.items() if not k.startswith("_")}

    def __repr__(self):
        return f"ProjectMemory(project={self.project}, keys={self.list_keys()})"