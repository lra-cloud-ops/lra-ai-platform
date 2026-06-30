# core/memory/organization_memory.py
import json
from pathlib import Path
from datetime import datetime
from core.interfaces.memory import Memory


class OrganizationMemory(Memory):
    """
    Memoria compartida por toda la organización LRA CloudOps.
    Contiene estándares, políticas y módulos reutilizables.
    Persistencia: memory/_organization/context.json
    Ver MEMORY.md §4.

    Defaults que hereda cualquier proyecto nuevo:
        naming_convention: kebab-case
        default_region: eu-west-1
        required_tags: [team, environment, cost-center]
    """

    DEFAULT_ORG_VALUES = {
        "naming_convention": "kebab-case",
        "default_region": "eu-west-1",
        "default_org": "lra-cloud-ops",
        "required_tags": ["team", "environment", "cost-center"],
        "terraform_modules": {
            "vpc": "github.com/lra-cloud-ops/terraform-vpc-module",
            "eks": "github.com/lra-cloud-ops/terraform-eks-module",
        },
        "documentation_standards": ["README.md", "ARCHITECTURE.md", "ROADMAP.md"],
    }

    def __init__(self, base_dir: str = "memory"):
        super().__init__(project="_organization")
        self.base_dir = Path(base_dir)
        self.org_dir = self.base_dir / "_organization"
        self.context_file = self.org_dir / "context.json"
        self._ensure_dirs()
        self._data = self._load_from_disk()
        self._seed_defaults()

    def _ensure_dirs(self):
        self.org_dir.mkdir(parents=True, exist_ok=True)

    def _load_from_disk(self) -> dict:
        if self.context_file.exists():
            with open(self.context_file, "r") as f:
                return json.load(f)
        return {}

    def _save_to_disk(self):
        with open(self.context_file, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    def _seed_defaults(self):
        """Escribe los defaults la primera vez que se crea la memoria."""
        if not self._data:
            self._data = dict(self.DEFAULT_ORG_VALUES)
            self._data["_created_at"] = datetime.now().isoformat()
            self._save_to_disk()

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
        self._seed_defaults()

    def list_keys(self) -> list:
        return [k for k in self._data.keys() if not k.startswith("_")]

    def snapshot(self) -> dict:
        return {k: v for k, v in self._data.items() if not k.startswith("_")}

    def __repr__(self):
        return f"OrganizationMemory(keys={self.list_keys()})"