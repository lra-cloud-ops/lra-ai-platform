# core/memory/workflow_memory.py
import json
from pathlib import Path
from datetime import datetime
from core.interfaces.memory import Memory


class WorkflowMemory(Memory):
    """
    Memoria efímera de un Execution Plan en curso.
    Vive mientras el plan está activo; se archiva al completarse.
    Persistencia: memory/_workflows/<plan_id>/context.json
    Ver MEMORY.md §6.

    Uso típico: una Task guarda el vpc_id que genera,
    la siguiente Task lo lee sin tener que buscarlo en AWS.
    """

    def __init__(self, plan_id: str, base_dir: str = "memory"):
        super().__init__(project=plan_id)
        self.plan_id = plan_id
        self.base_dir = Path(base_dir)
        self.plan_dir = self.base_dir / "_workflows" / plan_id
        self.context_file = self.plan_dir / "context.json"
        self._archived = False
        self._ensure_dirs()
        self._data = self._load_from_disk()

    def _ensure_dirs(self):
        self.plan_dir.mkdir(parents=True, exist_ok=True)

    def _load_from_disk(self) -> dict:
        if self.context_file.exists():
            with open(self.context_file, "r") as f:
                return json.load(f)
        return {}

    def _save_to_disk(self):
        with open(self.context_file, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def save(self, key: str, value) -> None:
        if self._archived:
            raise RuntimeError(f"WorkflowMemory for plan {self.plan_id} is archived.")
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

    def archive(self) -> dict:
        """
        Marca la memoria como solo lectura al completarse el plan.
        Retorna el snapshot para que WorkflowEngine pueda promover
        valores relevantes a ProjectMemory (MEMORY.md §8).
        """
        self._archived = True
        self._data["_archived_at"] = datetime.now().isoformat()
        self._save_to_disk()
        return self.snapshot()

    def is_archived(self) -> bool:
        return self._archived

    def __repr__(self):
        return f"WorkflowMemory(plan_id={self.plan_id}, archived={self._archived})"