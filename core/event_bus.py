# core/event_bus.py
# Sistema de comunicación interna entre componentes de LRA AI Platform.
# Implementa el patrón Publish/Subscribe (similar a Kafka o AWS SNS pero ligero).

from datetime import datetime
from typing import Callable
from dataclasses import dataclass, field


@dataclass
class Event:
    """
    Representa un evento en la plataforma.

    Ejemplos de eventos:
        type="agent.started"      → un agente comenzó a trabajar
        type="tool.executed"      → una tool ejecutó una acción
        type="task.completed"     → una tarea fue completada
        type="task.failed"        → una tarea falló
        type="project.registered" → un proyecto fue registrado
        type="memory.updated"     → la memoria de un proyecto fue actualizada
    """
    type: str
    data: dict = field(default_factory=dict)
    source: str = "platform"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def __repr__(self):
        return f"Event(type={self.type}, source={self.source}, timestamp={self.timestamp})"


class EventBus:
    """
    Bus de eventos central de LRA AI Platform.

    Permite que los componentes se comuniquen sin conocerse directamente.
    Un componente publica un evento. Otros componentes se suscriben a ese evento.

    Patrón: Publish/Subscribe
    Similar a: Kafka, RabbitMQ, AWS SNS, Redis Pub/Sub

    Uso:
        # Suscribirse a un evento
        bus.subscribe("task.completed", my_handler)

        # Publicar un evento
        bus.publish(Event(type="task.completed", data={"task": "deploy", "status": "ok"}))

        # El handler recibe el evento automáticamente
        def my_handler(event: Event):
            print(f"Task completed: {event.data}")
    """

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._history: list[Event] = []
        self._max_history: int = 100

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Suscribe un handler a un tipo de evento.
        El handler será llamado cada vez que se publique ese evento.

        Ejemplo:
            bus.subscribe("task.completed", on_task_completed)
            bus.subscribe("tool.executed", logger.log_tool_execution)
            bus.subscribe("*", dashboard.update)  # wildcard: todos los eventos
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Elimina la suscripción de un handler a un tipo de evento.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: Event) -> None:
        """
        Publica un evento en el bus.
        Todos los handlers suscritos a ese tipo de evento serán llamados.
        También llama a los handlers suscritos a '*' (wildcard).

        Ejemplo:
            bus.publish(Event(
                type="agent.started",
                source="devops",
                data={"task": "deploy lracloudops"}
            ))
        """
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        # Llamar handlers específicos del tipo de evento
        handlers = self._subscribers.get(event.type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus ERROR] Handler failed for event '{event.type}': {e}")

        # Llamar handlers wildcard (suscritos a todos los eventos)
        wildcard_handlers = self._subscribers.get("*", [])
        for handler in wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[EventBus ERROR] Wildcard handler failed: {e}")

    def get_history(self, event_type: str = None) -> list[Event]:
        """
        Retorna el historial de eventos.
        Si se especifica event_type, filtra por ese tipo.

        Ejemplo:
            bus.get_history()                    → todos los eventos
            bus.get_history("task.completed")    → solo tareas completadas
            bus.get_history("tool.executed")     → solo ejecuciones de tools
        """
        if event_type:
            return [e for e in self._history if e.type == event_type]
        return list(self._history)

    def clear_history(self) -> None:
        """Limpia el historial de eventos."""
        self._history = []

    def list_subscriptions(self) -> dict:
        """
        Retorna todas las suscripciones activas.
        Útil para debugging y para el dashboard.
        """
        return {
            event_type: len(handlers)
            for event_type, handlers in self._subscribers.items()
        }

    def summary(self) -> dict:
        """Retorna un resumen del estado del EventBus."""
        return {
            "total_events_in_history": len(self._history),
            "active_subscriptions": len(self._subscribers),
            "subscription_types": list(self._subscribers.keys()),
        }

    def __repr__(self):
        return (
            f"EventBus("
            f"subscriptions={len(self._subscribers)}, "
            f"history={len(self._history)})"
        )