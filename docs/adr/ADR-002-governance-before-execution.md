# ADR-002: Governance se evalúa antes de la ejecución, no después

**Estado:** Aceptado
**Fecha:** 2026-06-30
**Relacionado:** ARCHITECTURE.md, TASK_ENGINE.md, GOVERNANCE.md (pendiente)

---

## Contexto

Con Task como unidad central (ADR-001), queda por decidir en qué punto del
flujo se aplican las políticas de seguridad, los niveles de permiso y las
aprobaciones humanas: ¿antes de que una Task llegue a una Tool, o se deja
que la Tool se ejecute y se audita después?

## Problema

Un agente con acceso directo a una Tool puede ejecutar una acción
irreversible (ej. `terraform destroy`, eliminar un cluster EKS) antes de
que exista ningún control. Auditar después de los hechos sirve para
trazabilidad, pero no previene el daño.

## Alternativas consideradas

**A. Ejecutar primero, auditar después**
Descartado. El Audit Log sería un historial de lo ya ocurrido, no un
mecanismo de prevención. Inaceptable para acciones sobre producción.

**B. Governance opcional, activable solo en producción**
Descartado. Introduce dos caminos de código distintos (con y sin
Governance), lo que aumenta la superficie de bugs y la posibilidad de que
un entorno "no crítico" escale sin control a producción por error de
configuración.

**C. Toda Task pasa por Governance antes de llegar a una Capability/Tool**
(elegida)
Una Task nace en estado `PENDING` y nunca se ejecuta sin que Governance
emita una decisión (`APPROVED` o `REJECTED`). Esto es uniforme: aplica
igual a una Task de solo lectura que a un `terraform apply` en producción
— la diferencia está en la política configurada (ej. lectura = aprobación
automática; producción = aprobación humana obligatoria), no en si existe
o no el control.

## Decisión

Ninguna Task transiciona de `PENDING` a `RUNNING` sin pasar por el
Governance Engine. El Governance Engine evalúa, como mínimo:

- Nivel de permiso requerido por el tipo de Task (ver niveles 1-5 en
  GOVERNANCE.md)
- Políticas aplicables al entorno (ej. producción exige
  `security_scan` + `approval` + `architecture_review` antes de permitir
  un deploy)
- Si la decisión requiere intervención humana, la Task queda en estado
  `PENDING` visible en el Dashboard hasta recibir aprobación o rechazo

## Consecuencias

**Positivas:**
- Ninguna acción irreversible puede ocurrir sin pasar por un punto de
  control explícito, configurable por política.
- El mismo mecanismo sirve para Tasks triviales (lectura, sin fricción) y
  Tasks críticas (producción, con aprobación obligatoria) — solo cambia la
  política, no el código.
- La auditoría queda completa por diseño: toda Task tiene una decisión de
  Governance asociada desde el momento en que se crea.

**Negativas / costos asumidos:**
- Introduce latencia en el flujo: ninguna Task se ejecuta instantáneamente,
  incluso las de solo lectura pasan por una evaluación de política (aunque
  esta puede resolverse en milisegundos para casos de bajo riesgo).
- El Governance Engine se convierte en un punto crítico del sistema: si
  falla, ninguna Task puede ejecutarse. Debe diseñarse con alta
  disponibilidad y fallar de forma segura (denegar por defecto, nunca
  aprobar por defecto ante un error interno).

## Referencias

- ADR-001 — Task como unidad central
- GOVERNANCE.md (pendiente de redacción) — niveles de permiso, RBAC,
  Approval Engine, Policy Engine, Audit Log
