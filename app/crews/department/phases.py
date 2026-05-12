import json
from crewai import Crew, Process, Task, Agent
from app.core.datos_requeridos import (
    extraer_datos_del_mensaje,
    validar_datos_para_acciones,
)

def procesar_recoleccion(crew_instance, mensaje_usuario: str, contexto_chat: str) -> str:
    """Modo rápido: el cliente está dando datos que le pedimos."""
    print("\n[DATA] Modo Recoleccion: Extrayendo datos adicionales...")

    # Extraer datos del nuevo mensaje
    datos_nuevos = extraer_datos_del_mensaje(mensaje_usuario)
    print(f"[INFO] Datos nuevos extraidos: {datos_nuevos}")

    # Acumular
    crew_instance.datos_acumulados.update(datos_nuevos)
    print(f"[DATA] Datos acumulados totales: {crew_instance.datos_acumulados}")

    # Re-validar con las acciones pendientes
    acciones_aprobadas, acciones_bloqueadas, datos_faltantes = (
        validar_datos_para_acciones(crew_instance.acciones_pendientes, crew_instance.datos_acumulados)
    )

    print(f"[OK] Acciones ahora aprobadas: {acciones_aprobadas}")
    if acciones_bloqueadas:
        print(f"[WAIT] Aun faltan datos para: {acciones_bloqueadas}")

    # ¿Ya tenemos todo?
    if acciones_aprobadas and not acciones_bloqueadas:
        print("\n[SUCCESS] ¡Todos los datos recolectados! Ejecutando operaciones...")
        crew_instance.estado = crew_instance.ESTADO_IDLE
        crew_instance.acciones_pendientes = []
        crew_instance.datos_faltantes_actuales = []
        reporte = ejecutar_backoffice(crew_instance, acciones_aprobadas, contexto_chat)
        return generar_respuesta(crew_instance, mensaje_usuario, reporte, [], contexto_chat)

    elif acciones_aprobadas and acciones_bloqueadas:
        print(f"\n[⚡] Ejecutando acciones parciales: {acciones_aprobadas}")
        crew_instance.acciones_pendientes = acciones_bloqueadas
        crew_instance.datos_faltantes_actuales = datos_faltantes
        reporte = ejecutar_backoffice(crew_instance, acciones_aprobadas, contexto_chat)
        return generar_respuesta(crew_instance, mensaje_usuario, reporte, datos_faltantes, contexto_chat)

    else:
        crew_instance.acciones_pendientes = acciones_bloqueadas
        crew_instance.datos_faltantes_actuales = datos_faltantes
        return generar_respuesta(
            crew_instance,
            mensaje_usuario,
            "No se requirieron acciones en el CRM.",
            datos_faltantes,
            contexto_chat,
        )

def procesar_pipeline_completo(crew_instance, mensaje_usuario: str, contexto_chat: str) -> str:
    """Pipeline completo: clasificación → extracción → validación → ejecución → respuesta."""
    print("\n[PLAN] Fase 1: Analisis Dinamico del Mensaje (Con Memoria)...")

    agente_enrutador = crew_instance.agentes.agente_enrutador()

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

    for char in [".", '"', "'", "\n"]:
        lista_acciones_str = lista_acciones_str.replace(char, "")

    acciones = [acc.strip() for acc in lista_acciones_str.split(",") if acc.strip()]

    if "OPORTUNIDAD_CREAR" in acciones:
        if "COMPANIA_CREAR" not in acciones:
            acciones.append("COMPANIA_CREAR")
        if "PERSONA_CREAR" not in acciones:
            acciones.append("PERSONA_CREAR")

    print(f"[PLAN] Plan de Accion detectado: {acciones}\n")

    print("[DATA] Fase 1.5: Extrayendo datos reales del mensaje...")
    datos_nuevos = extraer_datos_del_mensaje(mensaje_usuario)
    print(f"[INFO] Datos extraidos de este mensaje: {datos_nuevos}")

    crew_instance.datos_acumulados.update(datos_nuevos)
    print(f"[DATA] Datos acumulados totales: {crew_instance.datos_acumulados}")

    acciones_aprobadas, acciones_bloqueadas, datos_faltantes = (
        validar_datos_para_acciones(acciones, crew_instance.datos_acumulados)
    )

    print(f"[OK] Acciones aprobadas (tienen datos): {acciones_aprobadas}")
    if acciones_bloqueadas:
        print(f"[WAIT] Acciones bloqueadas (faltan datos): {acciones_bloqueadas}")
        crew_instance.estado = crew_instance.ESTADO_RECOLECTANDO
        crew_instance.acciones_pendientes = acciones_bloqueadas
        crew_instance.datos_faltantes_actuales = datos_faltantes

    reporte_backoffice = "No se requirieron acciones en el CRM."
    acciones_crm = [a for a in acciones_aprobadas if a != "RESPONDER_FAQ"]
    if acciones_crm:
        reporte_backoffice = ejecutar_backoffice(crew_instance, acciones_crm, contexto_chat)

    return generar_respuesta(crew_instance, mensaje_usuario, reporte_backoffice, datos_faltantes, contexto_chat)

def ejecutar_backoffice(crew_instance, acciones: list, contexto_chat: str) -> str:
    """Ejecuta las operaciones de back-office en el CRM."""
    agentes_activos = []
    tareas_activas = []

    print("\n[CRM] Fase 2: Ejecutando operaciones silenciosas en el CRM...")

    acciones_compania = [acc for acc in acciones if acc.startswith("COMPANIA_")]
    if acciones_compania:
        agente_b2b = crew_instance.agentes.agente_gestor_companias()
        agentes_activos.append(agente_b2b)
        tareas_activas.append(
            crew_instance.tareas.tarea_gestionar_compania(
                agente_b2b, contexto_chat, acciones_compania[0],
                datos_validados=crew_instance.datos_acumulados
            )
        )

    acciones_persona = [acc for acc in acciones if acc.startswith("PERSONA_")]
    if acciones_persona:
        agente_per = crew_instance.agentes.agente_gestor_personas()
        agentes_activos.append(agente_per)
        tareas_activas.append(
            crew_instance.tareas.tarea_gestionar_persona(
                agente_per, contexto_chat, acciones_persona[0],
                datos_validados=crew_instance.datos_acumulados
            )
        )

    acciones_oportunidad = [acc for acc in acciones if acc.startswith("OPORTUNIDAD_")]
    if acciones_oportunidad:
        agente_ventas = crew_instance.agentes.agente_gestor_oportunidades()
        agentes_activos.append(agente_ventas)
        tareas_activas.append(
            crew_instance.tareas.tarea_gestionar_oportunidad(
                agente_ventas, contexto_chat, acciones_oportunidad[0],
                datos_validados=crew_instance.datos_acumulados
            )
        )

    acciones_ticket = [acc for acc in acciones if acc.startswith("TICKET_")]
    if acciones_ticket:
        agente_soporte = crew_instance.agentes.agente_gestor_tickets()
        agentes_activos.append(agente_soporte)
        tareas_activas.append(
            crew_instance.tareas.tarea_gestionar_ticket(
                agente_soporte, contexto_chat, acciones_ticket[0],
                datos_validados=crew_instance.datos_acumulados
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

    lista_reportes = []
    for t in tareas_activas:
        if hasattr(t, "output") and t.output and hasattr(t.output, "raw_output"):
            lista_reportes.append(t.output.raw_output)
        elif hasattr(t, "output") and t.output and hasattr(t.output, "raw"):
            lista_reportes.append(t.output.raw)

    reporte = " | ".join(lista_reportes) if lista_reportes else "Operaciones ejecutadas."
    print(f"[OK] Back-office finalizado. Reporte: {reporte[:150]}...\n")

    crew_instance.historial_chat.append(f"[Memoria Interna CRM]: {reporte}")
    return reporte

def generar_respuesta(crew_instance, mensaje_usuario: str, reporte_backoffice: str,
                       datos_faltantes: list, contexto_chat: str) -> str:
    """Genera la respuesta final de la Recepcionista."""
    print("[FRONT] Fase 3: Preparando respuesta para el cliente...")

    from app.tools.faq_tools import leer_faqs_empresa

    instruccion_datos_faltantes = ""
    if datos_faltantes:
        lista_faltantes = ", ".join(datos_faltantes)
        instruccion_datos_faltantes = (
            f"\n6. DATOS FALTANTES (¡OBLIGATORIO!): Necesitamos que el cliente nos dé: {lista_faltantes}. "
            f"Pídele esta información de forma amable y natural, integrándola en tu respuesta. "
            f"NO le digas que 'no pudimos procesar su solicitud'. Simplemente pídele los datos como "
            f"parte normal de la conversación."
        )

    resumen_datos = ""
    if crew_instance.datos_acumulados:
        resumen_datos = (
            f"\n\nDatos que YA tenemos del cliente (NO los pidas de nuevo): "
            f"{json.dumps(crew_instance.datos_acumulados, ensure_ascii=False)}"
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
        llm=crew_instance.agentes.llm,
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

    crew_instance.historial_chat.append(f"Asistente: {respuesta_final}")

    if crew_instance.estado == crew_instance.ESTADO_IDLE:
        crew_instance.acciones_pendientes = []

    return respuesta_final
