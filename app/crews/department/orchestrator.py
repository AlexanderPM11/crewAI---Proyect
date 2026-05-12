from app.agents.crm_agents import AgentesDepartamentoCRM
from app.tasks.crm_tasks import TareasDepartamentoCRM
from app.crews.department.constants import PALABRAS_CANCELAR
from app.crews.department.phases import (
    procesar_recoleccion,
    procesar_pipeline_completo,
)

class DepartamentoCRMCrew:
    # Estados de la conversación
    ESTADO_IDLE = "IDLE"
    ESTADO_RECOLECTANDO = "RECOLECTANDO_DATOS"

    def __init__(self):
        self.agentes = AgentesDepartamentoCRM()
        self.tareas = TareasDepartamentoCRM()
        self.historial_chat = []
        self.acciones_pendientes = []
        self.datos_acumulados = {}
        self.estado = self.ESTADO_IDLE
        self.datos_faltantes_actuales = []

    def _detectar_cancelacion(self, mensaje: str) -> bool:
        """Detecta si el cliente quiere cancelar el flujo actual."""
        msg_lower = mensaje.lower().strip()
        return any(palabra in msg_lower for palabra in PALABRAS_CANCELAR)

    def _resetear_flujo(self):
        """Limpia el estado de recolección para empezar de cero."""
        self.acciones_pendientes = []
        self.datos_acumulados = {}
        self.estado = self.ESTADO_IDLE
        self.datos_faltantes_actuales = []
        print("[RESET] Flujo reiniciado. Volviendo a modo normal.")

    def procesar_solicitud(self, mensaje_usuario: str) -> str:
        # 1. Agregamos el mensaje del usuario a la memoria completa
        self.historial_chat.append(f"Cliente: {mensaje_usuario}")

        # Contexto amplio: últimos 10 mensajes para mejor memoria
        contexto_chat = "\n".join(self.historial_chat[-10:])

        # DETECCIÓN DE CANCELACIÓN
        if self.estado == self.ESTADO_RECOLECTANDO and self._detectar_cancelacion(mensaje_usuario):
            self._resetear_flujo()

        # MODO RECOLECCIÓN
        if self.estado == self.ESTADO_RECOLECTANDO and self.acciones_pendientes:
            return procesar_recoleccion(self, mensaje_usuario, contexto_chat)

        # MODO NORMAL
        return procesar_pipeline_completo(self, mensaje_usuario, contexto_chat)
