from app.agents.crm_agents import AgentesDepartamentoCRM
from app.tasks.crm_tasks import TareasDepartamentoCRM
from app.crews.department.constants import PALABRAS_CANCELAR
from app.crews.department.phases import procesar_pipeline_agente
from app.core.datos_requeridos import extraer_datos_del_mensaje

class DepartamentoCRMCrew:
    ESTADO_IDLE = "IDLE"
    ESTADO_RECOLECTANDO = "RECOLECTANDO_DATOS"

    def __init__(self, initial_history=None):
        self.agentes = AgentesDepartamentoCRM()
        self.tareas = TareasDepartamentoCRM()
        self.historial_chat = initial_history if initial_history else []
        self.acciones_pendientes = []
        self.datos_acumulados = {}
        self.estado = self.ESTADO_IDLE
        self.datos_faltantes_actuales = []
        
        # Reconstruir memoria si hay historial previo
        if self.historial_chat:
            self._reconstruir_memoria()

    def _reconstruir_memoria(self):
        """Extrae datos estructurados del historial completo para pre-llenar la memoria."""
        print(f"\n[MEMORY] 🧠 Analizando historial para reconstruir memoria estructurada...")
        texto_completo = "\n".join(self.historial_chat)
        
        # Intentamos extraer datos del historial completo
        datos_extraidos = extraer_datos_del_mensaje(texto_completo)
        
        if datos_extraidos:
            # Limpiar datos que sean simplemente placeholders
            datos_limpios = {k: v for k, v in datos_extraidos.items() if str(v).lower() not in ["null", "none", "por definir", "aún por definir"]}
            print(f"[MEMORY] ✅ Datos recuperados del historial: {datos_limpios}")
            self.datos_acumulados.update(datos_limpios)
        else:
            print(f"[MEMORY] ℹ️ No se encontraron datos estructurados en el historial.")

    def _detectar_cancelacion(self, mensaje: str) -> bool:
        msg_lower = mensaje.lower().strip()
        return any(palabra in msg_lower for palabra in PALABRAS_CANCELAR)

    def _resetear_flujo(self):
        self.acciones_pendientes = []
        self.datos_acumulados = {}
        self.estado = self.ESTADO_IDLE
        self.datos_faltantes_actuales = []

    def procesar_solicitud(self, mensaje_usuario: str) -> str:
        # Agregamos el mensaje del usuario a la memoria local si no viene del historial cargado
        # (Aunque usualmente api.py se encarga de guardar y cargar)
        if not self.historial_chat or self.historial_chat[-1] != f"Cliente: {mensaje_usuario}":
            self.historial_chat.append(f"Cliente: {mensaje_usuario}")

        contexto_chat = "\n".join(self.historial_chat[-12:])

        if self.estado == self.ESTADO_RECOLECTANDO and self._detectar_cancelacion(mensaje_usuario):
            self._resetear_flujo()

        return procesar_pipeline_agente(self, mensaje_usuario, contexto_chat)
