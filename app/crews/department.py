from crewai import Crew, Process, Task, Agent
from app.agents.crm_agents import AgentesDepartamentoCRM
from app.tasks.crm_tasks import TareasDepartamentoCRM
from app.core.datos_requeridos import (
    extraer_datos_del_mensaje,
    validar_datos_para_acciones,
    DATOS_REQUERIDOS,
)
import json


# Palabras clave que indican que el cliente quiere cambiar de tema o cancelar
PALABRAS_CANCELAR = [
    "cancelar", "cancel", "olvidalo", "olvídalo", "no importa", "dejalo", "déjalo",
    "cambiar", "otra cosa", "mejor no", "no quiero",
]


class DepartamentoCRMCrew:
    # Estados de la conversación
    ESTADO_IDLE = "IDLE"  # Sin flujo activo, clasificar normalmente
    ESTADO_RECOLECTANDO = "RECOLECTANDO_DATOS"  # Pidiendo datos al cliente

    def __init__(self):
        self.agentes = AgentesDepartamentoCRM()
        self.tareas = TareasDepartamentoCRM()
        self.historial_chat = []  # Memoria completa de conversación
        self.acciones_pendientes = []  # Acciones bloqueadas esperando datos
        self.datos_acumulados = {}  # Datos del cliente acumulados entre turnos
        self.estado = self.ESTADO_IDLE  # Estado actual de la conversación
        self.datos_faltantes_actuales = []  # Lo que estamos pidiendo ahora

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

        # =====================================================================
        # DETECCIÓN DE CANCELACIÓN
        # =====================================================================
        if self.estado == self.ESTADO_RECOLECTANDO and self._detectar_cancelacion(mensaje_usuario):
            self._resetear_flujo()
            # Caer al flujo normal para clasificar la nueva intención

        # =====================================================================
        # MODO RECOLECCIÓN: Atajo rápido (sin re-clasificar)
        # =====================================================================
        if self.estado == self.ESTADO_RECOLECTANDO and self.acciones_pendientes:
            return self._procesar_recoleccion(mensaje_usuario, contexto_chat)

        # =====================================================================
        # MODO NORMAL: Pipeline completo
        # =====================================================================
        return self._procesar_pipeline_completo(mensaje_usuario, contexto_chat)

    def _procesar_recoleccion(self, mensaje_usuario: str, contexto_chat: str) -> str:
        """
        Modo rápido: el cliente está dando datos que le pedimos.
        NO re-clasificamos, solo extraemos datos y verificamos si ya tenemos todo.
        """
        print("\n[DATA] Modo Recoleccion: Extrayendo datos adicionales...")

        # Extraer datos del nuevo mensaje
        datos_nuevos = extraer_datos_del_mensaje(mensaje_usuario)
        print(f"[INFO] Datos nuevos extraidos: {datos_nuevos}")

        # Acumular
        self.datos_acumulados.update(datos_nuevos)
        print(f"[DATA] Datos acumulados totales: {self.datos_acumulados}")

        # Re-validar con las acciones pendientes
        acciones_aprobadas, acciones_bloqueadas, datos_faltantes = (
            validar_datos_para_acciones(self.acciones_pendientes, self.datos_acumulados)
        )

        print(f"[OK] Acciones ahora aprobadas: {acciones_aprobadas}")
        if acciones_bloqueadas:
            print(f"[WAIT] Aun faltan datos para: {acciones_bloqueadas}")

        # ¿Ya tenemos todo?
        if acciones_aprobadas and not acciones_bloqueadas:
            # ¡Datos completos! Ejecutar el back-office y responder
            print("\n[SUCCESS] ¡Todos los datos recolectados! Ejecutando operaciones...")
            self.estado = self.ESTADO_IDLE
            self.acciones_pendientes = []
            self.datos_faltantes_actuales = []
            reporte = self._ejecutar_backoffice(acciones_aprobadas, contexto_chat)
            return self._generar_respuesta(mensaje_usuario, reporte, [], contexto_chat)

        elif acciones_aprobadas and acciones_bloqueadas:
            # Tenemos datos parciales, ejecutar lo que se pueda
            print(f"\n[⚡] Ejecutando acciones parciales: {acciones_aprobadas}")
            self.acciones_pendientes = acciones_bloqueadas
            self.datos_faltantes_actuales = datos_faltantes
            reporte = self._ejecutar_backoffice(acciones_aprobadas, contexto_chat)
            return self._generar_respuesta(mensaje_usuario, reporte, datos_faltantes, contexto_chat)

        else:
            # Seguimos sin datos suficientes, pedir de nuevo
            self.acciones_pendientes = acciones_bloqueadas
            self.datos_faltantes_actuales = datos_faltantes
            return self._generar_respuesta(
                mensaje_usuario,
                "No se requirieron acciones en el CRM.",
                datos_faltantes,
                contexto_chat,
            )

    def _procesar_pipeline_completo(self, mensaje_usuario: str, contexto_chat: str) -> str:
        """Pipeline completo: clasificación → extracción → validación → ejecución → respuesta."""

        # =====================================================================
        # FASE 1: CLASIFICACIÓN DE INTENCIÓN
        # =====================================================================
        print("\n[PLAN] Fase 1: Analisis Dinamico del Mensaje (Con Memoria)...")

        agente_enrutador = self.agentes.agente_enrutador()

        tarea_analisis_multiple = Task(
            description=(
                f"Analiza este historial reciente de conversación:\n"
                f"--- INICIO DEL CHAT ---\n{contexto_chat}\n--- FIN DEL CHAT ---\n\n"
                f"REGLAS DE CLASIFICACIÓN ESTRICTAS PARA EL ÚLTIMO MENSAJE:\n"
                f"1. PREGUNTAS GENERALES: Si el cliente SOLO está preguntando horarios, ubicación o dudas generales, devuelve ÚNICAMENTE: 'RESPONDER_FAQ'.\n"
                f"2. INTENCIÓN DE COMPRA: Si el cliente expresa interés en cotizar, comprar o necesitar un servicio (SIN IMPORTAR si es el primer o segundo mensaje), devuelve obligatoriamente: 'COMPANIA_CREAR, PERSONA_CREAR, OPORTUNIDAD_CREAR, RESPONDER_FAQ'.\n"
                f"3. SEGUIMIENTO (DATOS): Si el cliente está respondiendo con sus datos (correo o teléfono) para que le envíen información, devuelve SOLO: 'PERSONA_MODIFICAR'. NUNCA repitas acciones de crear si ya se hicieron.\n"
                f"4. SOPORTE: Si reporta una falla o problema técnico, devuelve: 'TICKET_CREAR'.\n\n"
                f"Opciones válidas: COMPANIA_CREAR, PERSONA_CREAR, PERSONA_MODIFICAR, OPORTUNIDAD_CREAR, TICKET_CREAR, RESPONDER_FAQ.\n\n"
                f"Evalúa inteligentemente la verdadera intención. Devuelve SOLO la lista de palabras clave separadas por comas. NADA MÁS."
            ),
            expected_output="Lista de acciones CRM separadas por comas, evaluando inteligentemente la intención del último mensaje.",
            agent=agente_enrutador,
            output_json=False,
        )

        crew_analisis = Crew(
            agents=[agente_enrutador],
            tasks=[tarea_analisis_multiple],
            process=Process.sequential,
            verbose=False,
        )
        lista_acciones_str = str(crew_analisis.kickoff()).strip().upper()

        # Limpieza básica
        for char in [".", '"', "'", "\n"]:
            lista_acciones_str = lista_acciones_str.replace(char, "")

        acciones = [acc.strip() for acc in lista_acciones_str.split(",") if acc.strip()]

        # Seguro de vida: si hay venta, forzar la trinidad
        if "OPORTUNIDAD_CREAR" in acciones:
            if "COMPANIA_CREAR" not in acciones:
                acciones.append("COMPANIA_CREAR")
            if "PERSONA_CREAR" not in acciones:
                acciones.append("PERSONA_CREAR")

        print(f"[PLAN] Plan de Accion detectado: {acciones}\n")

        # =====================================================================
        # FASE 1.5: EXTRACCIÓN Y VALIDACIÓN DE DATOS (ANTI-ALUCINACIÓN)
        # =====================================================================
        print("[DATA] Fase 1.5: Extrayendo datos reales del mensaje...")

        datos_nuevos = extraer_datos_del_mensaje(mensaje_usuario)
        print(f"[INFO] Datos extraidos de este mensaje: {datos_nuevos}")

        self.datos_acumulados.update(datos_nuevos)
        print(f"[DATA] Datos acumulados totales: {self.datos_acumulados}")

        acciones_aprobadas, acciones_bloqueadas, datos_faltantes = (
            validar_datos_para_acciones(acciones, self.datos_acumulados)
        )

        print(f"[OK] Acciones aprobadas (tienen datos): {acciones_aprobadas}")
        if acciones_bloqueadas:
            print(f"[WAIT] Acciones bloqueadas (faltan datos): {acciones_bloqueadas}")
            print(f"[INFO] Se pedira al cliente: {datos_faltantes}")
            # Cambiar a modo recolección
            self.estado = self.ESTADO_RECOLECTANDO
            self.acciones_pendientes = acciones_bloqueadas
            self.datos_faltantes_actuales = datos_faltantes

        # =====================================================================
        # FASE 2: TRABAJO DE BACK-OFFICE SILENCIOSO
        # =====================================================================
        reporte_backoffice = "No se requirieron acciones en el CRM."

        # Solo ejecutar si hay acciones de CRM aprobadas (no FAQ)
        acciones_crm = [a for a in acciones_aprobadas if a != "RESPONDER_FAQ"]
        if acciones_crm:
            reporte_backoffice = self._ejecutar_backoffice(acciones_crm, contexto_chat)

        # =====================================================================
        # FASE 3: RESPUESTA AL CLIENTE
        # =====================================================================
        return self._generar_respuesta(mensaje_usuario, reporte_backoffice, datos_faltantes, contexto_chat)

    def _ejecutar_backoffice(self, acciones: list, contexto_chat: str) -> str:
        """Ejecuta las operaciones de back-office en el CRM."""
        agentes_activos = []
        tareas_activas = []

        print("\n[CRM] Fase 2: Ejecutando operaciones silenciosas en el CRM...")

        acciones_compania = [acc for acc in acciones if acc.startswith("COMPANIA_")]
        if acciones_compania:
            agente_b2b = self.agentes.agente_gestor_companias()
            agentes_activos.append(agente_b2b)
            tareas_activas.append(
                self.tareas.tarea_gestionar_compania(
                    agente_b2b, contexto_chat, acciones_compania[0],
                    datos_validados=self.datos_acumulados
                )
            )

        acciones_persona = [acc for acc in acciones if acc.startswith("PERSONA_")]
        if acciones_persona:
            agente_per = self.agentes.agente_gestor_personas()
            agentes_activos.append(agente_per)
            tareas_activas.append(
                self.tareas.tarea_gestionar_persona(
                    agente_per, contexto_chat, acciones_persona[0],
                    datos_validados=self.datos_acumulados
                )
            )

        acciones_oportunidad = [acc for acc in acciones if acc.startswith("OPORTUNIDAD_")]
        if acciones_oportunidad:
            agente_ventas = self.agentes.agente_gestor_oportunidades()
            agentes_activos.append(agente_ventas)
            tareas_activas.append(
                self.tareas.tarea_gestionar_oportunidad(
                    agente_ventas, contexto_chat, acciones_oportunidad[0],
                    datos_validados=self.datos_acumulados
                )
            )

        acciones_ticket = [acc for acc in acciones if acc.startswith("TICKET_")]
        if acciones_ticket:
            agente_soporte = self.agentes.agente_gestor_tickets()
            agentes_activos.append(agente_soporte)
            tareas_activas.append(
                self.tareas.tarea_gestionar_ticket(
                    agente_soporte, contexto_chat, acciones_ticket[0],
                    datos_validados=self.datos_acumulados
                )
            )

        if not agentes_activos:
            return "No se requirieron acciones en el CRM."

        crew_backoffice = Crew(
            agents=agentes_activos,
            tasks=tareas_activas,
            process=Process.sequential,
            verbose=False,
        )
        crew_backoffice.kickoff()

        # Recolectar reportes
        lista_reportes = []
        for t in tareas_activas:
            if hasattr(t, "output") and t.output and hasattr(t.output, "raw_output"):
                lista_reportes.append(t.output.raw_output)
            elif hasattr(t, "output") and t.output and hasattr(t.output, "raw"):
                lista_reportes.append(t.output.raw)

        reporte = " | ".join(lista_reportes) if lista_reportes else "Operaciones ejecutadas."
        print(f"[OK] Back-office finalizado. Reporte: {reporte[:150]}...\n")

        # Guardar en memoria interna
        self.historial_chat.append(f"[Memoria Interna CRM]: {reporte}")

        return reporte

    def _generar_respuesta(self, mensaje_usuario: str, reporte_backoffice: str,
                           datos_faltantes: list, contexto_chat: str) -> str:
        """Genera la respuesta final de la Recepcionista."""
        print("[FRONT] Fase 3: Preparando respuesta para el cliente...")

        from app.tools.faq_tools import leer_faqs_empresa

        # Construir instrucción de datos faltantes
        instruccion_datos_faltantes = ""
        if datos_faltantes:
            lista_faltantes = ", ".join(datos_faltantes)
            instruccion_datos_faltantes = (
                f"\n6. DATOS FALTANTES (¡OBLIGATORIO!): Necesitamos que el cliente nos dé: {lista_faltantes}. "
                f"Pídele esta información de forma amable y natural, integrándola en tu respuesta. "
                f"NO le digas que 'no pudimos procesar su solicitud'. Simplemente pídele los datos como "
                f"parte normal de la conversación."
            )

        # Dar contexto completo al recepcionista
        resumen_datos = ""
        if self.datos_acumulados:
            resumen_datos = (
                f"\n\nDatos que YA tenemos del cliente (NO los pidas de nuevo): "
                f"{json.dumps(self.datos_acumulados, ensure_ascii=False)}"
            )

        agente_recepcionista = Agent(
            role="Especialista en Atención al Cliente y Asesoría",
            goal="Responder de forma breve, cálida y genuinamente amable. Máximo 2-3 oraciones.",
            backstory=(
                "Eres la cara amable de Triple Tecnología. Tu personalidad es cálida, entusiasta y cercana. "
                "SIEMPRE llamas al cliente por su nombre si lo conoces. "
                "Muestras interés genuino por su proyecto — si quiere una app, te emociona ayudarle. "
                "Hablas como un amigo profesional en WhatsApp: cercano pero confiable. "
                "NUNCA uses lenguaje corporativo frío ni respuestas genéricas. "
                "NUNCA menciones IDs, códigos ni detalles técnicos internos. "
                "NUNCA inventes precios ni servicios. "
                "Tienes una herramienta INTERNA llamada 'leer_faqs_empresa' para consultar info de servicios "
                "y precios. Úsala cuando necesites, pero NUNCA le digas al cliente que existen FAQs ni que lea nada. "
                "Tú eres el experto y le das la info directamente."
            ),
            tools=[leer_faqs_empresa],
            llm=self.agentes.llm,
            verbose=True,
            allow_delegation=False,
        )

        tarea_respuesta = Task(
            description=(
                f"Historial de conversación reciente:\n"
                f"--- INICIO ---\n{contexto_chat}\n--- FIN ---\n\n"
                f"Último mensaje del cliente: '{mensaje_usuario}'.\n"
                f"Reporte del Back-office: '{reporte_backoffice}'.{resumen_datos}\n\n"
                f"REGLAS DE RESPUESTA (sigue TODAS):\n"
                f"1. BREVEDAD: Responde en MÁXIMO 2-3 oraciones. Nada de párrafos largos.\n"
                f"2. PROHIBIDO: NUNCA menciones IDs, UUIDs, FAQs, herramientas internas, ni le digas al cliente que lea algo. Tú eres el experto y respondes directamente.\n"
                f"3. PRECIOS/SERVICIOS: Si el cliente preguntó por costos o servicios, usa la herramienta 'leer_faqs_empresa' INTERNAMENTE para obtener la info y respóndele tú directamente con esos datos.\n"
                f"4. NO REPITAS: Si el cliente ya dio un dato, NO lo pidas de nuevo.\n"
                f"5. ERRORES: Si el reporte dice 'Error', NO se lo digas al cliente. Di que el equipo lo contactará pronto.\n"
                f"6. TONO: Habla como en un chat de WhatsApp, no como un email corporativo."
                f"{instruccion_datos_faltantes}"
                f"{'' if datos_faltantes else chr(10) + '7. CIERRE CON PREGUNTA: SIEMPRE termina con una pregunta abierta como: ¿Hay algo más en lo que te pueda ayudar? o ¿Tienes alguna otra duda?'}"
            ),
            expected_output="Respuesta breve de máximo 2-3 oraciones. Sin IDs ni detalles técnicos.",
            agent=agente_recepcionista,
            output_json=False,
        )

        crew_respuesta = Crew(
            agents=[agente_recepcionista],
            tasks=[tarea_respuesta],
            process=Process.sequential,
            verbose=True,
        )
        respuesta_final = str(crew_respuesta.kickoff())

        # Guardar respuesta en memoria
        self.historial_chat.append(f"Asistente: {respuesta_final}")

        # Limpiar pendientes que ya se ejecutaron
        if self.estado == self.ESTADO_IDLE:
            self.acciones_pendientes = []

        return respuesta_final
