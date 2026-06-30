# core/memory/conversation_memory.py
from datetime import datetime
from core.interfaces.memory import Memory


class ConversationMemory(Memory):
    """
    Memoria de la sesión de conversación actual con el usuario.
    No persiste en disco — vive solo en RAM durante la sesión.
    Ver MEMORY.md §7.

    Permite que el Supervisor entienda referencias como
    'hazlo también para el segundo' sin que el usuario repita contexto.
    """

    def __init__(self, session_id: str):
        super().__init__(project=session_id)
        self.session_id = session_id
        self._data: dict = {}
        self._history: list = []

    def save(self, key: str, value) -> None:
        self._data[key] = value
        self._history.append({
            "key": key,
            "value": value,
            "timestamp": datetime.now().isoformat(),
        })

    def load(self, key: str):
        return self._data.get(key)

    def delete(self, key: str) -> None:
        if key in self._data:
            del self._data[key]

    def clear(self) -> None:
        self._data = {}
        self._history = []

    def list_keys(self) -> list:
        return list(self._data.keys())

    def snapshot(self) -> dict:
        return dict(self._data)

    def get_history(self) -> list:
        """Retorna el historial completo de la conversación."""
        return list(self._history)

    def add_message(self, role: str, content: str) -> None:
        """Registra un mensaje de la conversación (user o assistant)."""
        self._history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })

    def get_messages(self) -> list:
        """Retorna solo los mensajes (filtra entradas que no son mensajes)."""
        return [e for e in self._history if "role" in e]

    def __repr__(self):
        return f"ConversationMemory(session={self.session_id}, keys={self.list_keys()})"