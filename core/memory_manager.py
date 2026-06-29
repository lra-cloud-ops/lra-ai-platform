# core/memory_manager.py
# Gestiona la memoria independiente de cada proyecto registrado.

import json
import shutil
from pathlib import Path
from datetime import datetime
from core.interfaces.memory import Memory


class ProjectMemory(Memory):
    """
    Implementación concreta de Memory para un proyecto específico.
    Almacena el contexto en memory/<proyecto>/context.json
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


class MemoryManager:
    """
    Gestor central de memoria de LRA AI Platform.
    Mantiene una instancia de ProjectMemory por cada proyecto.
    """

    def __init__(self, base_dir: str = "memory"):
        self.base_dir = base_dir
        self._registry = {}

    def get_memory(self, project: str) -> ProjectMemory:
        if project not in self._registry:
            self._registry[project] = ProjectMemory(project, self.base_dir)
        return self._registry[project]

    def list_projects(self) -> list:
        base = Path(self.base_dir)
        if not base.exists():
            return []
        return [d.name for d in base.iterdir() if d.is_dir()]

    def delete_project(self, project: str) -> None:
        project_dir = Path(self.base_dir) / project
        if project_dir.exists():
            shutil.rmtree(project_dir)
        if project in self._registry:
            del self._registry[project]

    def summary(self) -> dict:
        projects = self.list_projects()
        return {
            "total_projects": len(projects),
            "projects": projects,
            "loaded_in_memory": list(self._registry.keys()),
        }

    def __repr__(self):
        return f"MemoryManager(projects={self.list_projects()})"