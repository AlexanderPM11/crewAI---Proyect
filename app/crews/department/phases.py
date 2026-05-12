import json
import re
from crewai import Crew, Process, Task, Agent
from app.core.datos_requeridos import (
    extraer_datos_del_mensaje,
    validar_datos_para_acciones,
)

def procesar_pipeline_agente(crew_instance, mensaje_usuario: str, contexto_chat: str) -> str:
    """
    Pipeline unificado y agentizado: un Estratega decide el curso de acción
    basándose en la memoria (ahora persistente) y el mensaje actual.
    """
    print("\n[STRATEGY] Fase 1: Análisis Estratégico por Agente...")

    agente_estratega = crew_instance.agentes.agente_estratega()
    
    tarea_estrategia = crew_instance.tareas.tarea_analisis_estrategico(
        agente_estratega, 
        mensaje_usuario, 
        contexto_chat, 
        crew_instance.datos_acumulados
    )

    crew_analisis = Crew(
        agents=[agente_estratega],
        tasks=[tarea_estrategia],
        process=Process.sequential,
        verbose=False,
    )
    
    resultado_raw = str(crew_analisis.kickoff()).strip()
    
    if "```json" in resultado_raw:
        resultado_raw = re.search(r"```json\n(.*?)\n```", resultado_raw, re.DOTALL).group(1)
    elif "```" in resultado_raw:
        resultado_raw = re.search(r"```\n(.*?)\n```", resultado_raw, re.DOTALL).group(1)

    try:
        estrategia = json.loads(resultado_raw)
    except Exception as e:
        print(f"[ERROR] No se pudo parsear el JSON de estrategia: {e}")
        estrategia = {"intencion": "desconocida", "acciones_crm": [], "datos_nuevos": {}, "datos_faltantes": [], "decision": "RESPONDER"}

    print(f"[STRATEGY] Decisión: {estrategia.get('decision')} | Acciones: {estrategia.get('acciones_crm')}")

    datos_agente = estrategia.get("datos_nuevos", {})
    if datos_agente:
        crew_instance.datos_acumulados.update(datos_agente)

    decision = estrategia.get("decision", "RESPONDER")
    acciones = estrategia.get("acciones_crm", [])
    datos_faltantes = estrategia.get("datos_faltantes", [])

    if decision == "EJECUTAR" and acciones:
        reporte = ejecutar_backoffice(crew_instance, acciones, contexto_chat)
        return generar_respuesta(crew_instance, mensaje_usuario, reporte, [], contexto_chat)
    elif decision == "PEDIR_DATOS":
        crew_instance.estado = crew_instance.ESTADO_RECOLECTANDO
        crew_instance.acciones_pendientes = acciones
        crew_instance.datos_faltantes_actuales = datos_faltantes
        return generar_respuesta(crew_instance, mensaje_usuario, "Esperando datos del cliente.", datos_faltantes, contexto_chat)
    else:
        return generar_respuesta(crew_instance, mensaje_usuario, "No se requirieron acciones en el CRM.", [], contexto_chat)

def ejecutar_backoffice(crew_instance, acciones: list, contexto_chat: str) -> str:
    """Ejecuta las operaciones de back-office en el CRM."""
    agentes_activos = []
    tareas_activas = []

    print("\n[CRM] Fase 2: Ejecutando operaciones silenciosas en el CRM...")

    # Mapeo simplificado
    for acc in acciones:
        if acc.startswith("COMPANIA_"):
            agente = crew_instance.agentes.agente_gestor_companias()
            agentes_activos.append(agente)
            tareas_activas.append(crew_instance.tareas.tarea_gestionar_compania(agente, contexto_chat, acc, datos_validados=crew_instance.datos_acumulados))
        elif acc.startswith("PERSONA_"):
            agente = crew_instance.agentes.agente_gestor_personas()
            agentes_activos.append(agente)
            tareas_activas.append(crew_instance.tareas.tarea_gestionar_persona(agente, contexto_chat, acc, datos_validados=crew_instance.datos_acumulados))
        elif acc.startswith("OPORTUNIDAD_"):
            agente = crew_instance.agentes.agente_gestor_oportunidades()
            agentes_activos.append(agente)
            tareas_activas.append(crew_instance.tareas.tarea_gestionar_oportunidad(agente, contexto_chat, acc, datos_validados=crew_instance.datos_acumulados))
        elif acc.startswith("TICKET_"):
            agente = crew_instance.agentes.agente_gestor_tickets()
            agentes_activos.append(agente)
            tareas_activas.append(crew_instance.tareas.tarea_gestionar_ticket(agente, contexto_chat, acc, datos_validados=crew_instance.datos_acumulados))

    if not agentes_activos:
        return "No se requirieron acciones."

    crew_backoffice = Crew(agents=agentes_activos, tasks=tareas_activas, process=Process.sequential, verbose=False)
    crew_backoffice.kickoff()

    lista_reportes = []
    for t in tareas_activas:
        if hasattr(t, "output") and t.output:
            lista_reportes.append(getattr(t.output, "raw_output", getattr(t.output, "raw", "")))

    reporte = " | ".join(lista_reportes) if lista_reportes else "Operaciones ejecutadas."
    crew_instance.historial_chat.append(f"[Memoria Interna CRM]: {reporte}")
    return reporte

def generar_respuesta(crew_instance, mensaje_usuario: str, reporte_backoffice: str,
                       datos_faltantes: list, contexto_chat: str) -> str:
    """Genera la respuesta final de la Recepcionista."""
    from app.tools.faq_tools import leer_faqs_empresa

    instruccion_datos_faltantes = f"\n6. DATOS FALTANTES: Pide amable: {', '.join(datos_faltantes)}" if datos_faltantes else ""
    resumen_datos = f"\n\nDatos actuales: {json.dumps(crew_instance.datos_acumulados, ensure_ascii=False)}" if crew_instance.datos_acumulados else ""

    agente_recepcionista = Agent(
        role="Especialista en Atención al Cliente y Asesoría",
        goal="Responder de forma breve, cálida y genuinamente amable. Máximo 2-3 oraciones.",
        backstory="Eres la cara amable de Triple Tecnología. Hablas como un amigo profesional en WhatsApp.",
        tools=[leer_faqs_empresa],
        llm=crew_instance.agentes.llm,
        verbose=True,
        allow_delegation=False,
    )

    tarea_respuesta = Task(
        description=(
            f"Historial de Chat:\n{contexto_chat}\n\n"
            f"Mensaje actual del cliente: '{mensaje_usuario}'\n"
            f"DATOS QUE YA CONOCEMOS: {json.dumps(crew_instance.datos_acumulados, ensure_ascii=False)}\n"
            f"REPORTE DEL EQUIPO TÉCNICO (Lo que se registró en el CRM): {reporte_backoffice}\n\n"
            f"INSTRUCCIONES:\n"
            f"1. Eres un Especialista en Atención al Cliente y Captación de Leads.\n"
            f"2. CONFIRMACIÓN: Si el reporte indica que se creó una oportunidad o persona, CONFÍRMALO al cliente de forma amable. Ejemplo: '¡Listo Alexander! Ya registré tu proyecto de App móvil y tu correo.'\n"
            f"3. RESPUESTA HÍBRIDA: Resuelve la duda técnica usando 'leer_faqs_empresa'.\n"
            f"4. CAPTACIÓN ACTIVA: Si faltan datos ({', '.join(datos_faltantes) if datos_faltantes else 'ninguno'}), pide UN solo dato. Si NO faltan datos, despídete cordialmente diciendo que el equipo lo contactará pronto.\n"
            f"5. REGLA DE ORO: Máximo 3-4 oraciones. Sé cálido, profesional y humano."
        ),
        expected_output="Respuesta humana que informa y solicita un dato para el CRM.",
        agent=agente_recepcionista,
    )

    crew_respuesta = Crew(agents=[agente_recepcionista], tasks=[tarea_respuesta], process=Process.sequential, verbose=True)
    respuesta_final = str(crew_respuesta.kickoff())
    crew_instance.historial_chat.append(f"Asistente: {respuesta_final}")
    return respuesta_final
