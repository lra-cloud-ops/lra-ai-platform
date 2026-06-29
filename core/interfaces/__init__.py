# core/interfaces/__init__.py
# Exporta todas las interfaces del módulo de forma limpia.

from core.interfaces.tool import Tool
from core.interfaces.agent import Agent
from core.interfaces.capability import Capability
from core.interfaces.memory import Memory

__all__ = ["Tool", "Agent", "Capability", "Memory"]