"""
Configuración de datos requeridos por cada operación CRM.
Define qué campos son obligatorios y opcionales para evitar
que los agentes alucinen datos que el cliente no ha proporcionado.
"""

import re
import json
from crewai import Crew, Process, Task
from app.core.llm_setup import llm_activo


# =====================================================================
# CAMPOS REQUERIDOS POR OPERACIÓN
# =====================================================================
DATOS_REQUERIDOS = {
    "COMPANIA_CREAR": {
        "campos_obligatorios": ["nombre_empresa"],
        "campos_opcionales": ["dominio_web", "empleados", "ciudad", "pais"],
        "pregunta_faltante": "el nombre de tu empresa o negocio",
    },
    "PERSONA_CREAR": {
        "campos_obligatorios": ["nombre_persona"],
        "campos_opcionales": ["apellido", "email", "telefono"],
        "pregunta_faltante": "tu nombre completo",
    },
    "OPORTUNIDAD_CREAR": {
        "campos_obligatorios": ["nombre_proyecto"],
        "campos_opcionales": ["presupuesto"],
        "pregunta_faltante": "qué servicio o proyecto necesitas",
    },
    "TICKET_CREAR": {
        "campos_obligatorios": ["descripcion_problema"],
        "campos_opcionales": [],
        "pregunta_faltante": "una descripción del problema que estás experimentando",
    },
}

# Todos los campos posibles que el LLM debe extraer
TODOS_LOS_CAMPOS = [
    "nombre_empresa", "dominio_web", "empleados", "ciudad", "pais",
    "nombre_persona", "apellido", "email", "telefono",
    "nombre_proyecto", "presupuesto",
    "descripcion_problema",
]


# =====================================================================
# EXTRACCIÓN HÍBRIDA (Regex + LLM)
# =====================================================================

def _extraer_con_regex(texto: str) -> dict:
    """Extrae datos estructurados con regex: email y teléfono."""
    datos = {}

    # Email
    match_email = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', texto)
    if match_email:
        datos["email"] = match_email.group(0)

    # Teléfono (formatos: +18095551234, 809-555-1234, (809) 555 1234, 8099160688, etc.)
    match_tel = re.search(r'(\+?\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}', texto)
    if match_tel:
        raw = match_tel.group(0)
        limpio = re.sub(r'[^\d+]', '', raw)
        # Si tiene 10 dígitos y no tiene +, asumimos RD/US (+1)
        if len(limpio) == 10 and not limpio.startswith('+'):
            limpio = '+1' + limpio
        datos["telefono"] = limpio

    return datos


def _extraer_con_llm(texto: str, agente_enrutador) -> dict:
    """Usa el LLM para extraer datos explícitamente mencionados en formato JSON."""
    from crewai import Agent

    agente_extractor = Agent(
        role="Extractor de Datos del Cliente",
        goal="Extraer ÚNICAMENTE los datos que el cliente haya mencionado explícitamente. NUNCA inventar datos.",
        backstory=(
            "Eres una máquina de extracción de datos. Tu trabajo es leer un mensaje "
            "y extraer SOLO la información que el cliente dijo textualmente. "
            "Si un dato NO fue mencionado, DEBES poner null. NUNCA inventes nombres, "
            "emails, teléfonos ni empresas. Es mejor dejar null que inventar."
        ),
        llm=llm_activo,
        verbose=False,
        allow_delegation=False,
    )

    campos_json = ", ".join([f'"{c}": "..." o null' for c in TODOS_LOS_CAMPOS])

    tarea_extraccion = Task(
        description=(
            f"Lee este mensaje del cliente y extrae SOLO los datos que mencionó explícitamente:\n\n"
            f"Mensaje: \"{texto}\"\n\n"
            f"REGLAS ESTRICTAS:\n"
            f"- Si el cliente NO mencionó un dato, pon null. NUNCA inventes.\n"
            f"- 'nombre_persona' es el primer nombre del cliente (ej: 'Juan').\n"
            f"- 'apellido' es el apellido del cliente.\n"
            f"- 'nombre_empresa' es el nombre de la compañía o negocio.\n"
            f"- 'nombre_proyecto' es lo que el cliente quiere cotizar o el servicio que necesita.\n"
            f"- 'descripcion_problema' es una falla técnica reportada.\n"
            f"- 'presupuesto' es un número de dinero mencionado.\n\n"
            f"Responde SOLO con este JSON exacto, sin texto adicional:\n"
            f"{{{campos_json}}}"
        ),
        expected_output="Un JSON con los datos extraídos. Campos no mencionados deben ser null.",
        agent=agente_extractor,
        output_json=False,
    )

    crew_ext = Crew(
        agents=[agente_extractor],
        tasks=[tarea_extraccion],
        process=Process.sequential,
        verbose=False,
    )

    resultado = str(crew_ext.kickoff()).strip()

    # Intentar parsear el JSON de la respuesta del LLM
    try:
        # Buscar el JSON dentro de la respuesta (puede tener texto extra)
        match = re.search(r'\{[^{}]*\}', resultado, re.DOTALL)
        if match:
            datos_raw = json.loads(match.group(0))
        else:
            datos_raw = json.loads(resultado)

        # Filtrar nulls y strings vacíos
        datos = {}
        for k, v in datos_raw.items():
            val_str = str(v).lower().strip()
            if v is not None and val_str not in ["null", "none", "", "desconocido", "n/a", "undefined"]:
                datos[k] = str(v)
        return datos
    except (json.JSONDecodeError, AttributeError):
        return {}


def extraer_datos_del_mensaje(texto: str, agente_enrutador=None) -> dict:
    """
    Extracción híbrida: primero regex (rápido y confiable) para emails/teléfonos,
    luego LLM para nombres, empresas y descripciones.
    """
    # Paso 1: Regex (determinístico)
    datos_regex = _extraer_con_regex(texto)

    # Paso 2: LLM (flexible)
    datos_llm = _extraer_con_llm(texto, agente_enrutador)

    # Merge: regex tiene prioridad (más confiable)
    datos_finales = {**datos_llm, **datos_regex}

    return datos_finales


def validar_datos_para_acciones(acciones: list, datos: dict) -> tuple:
    """
    Valida si tenemos los datos mínimos para cada acción.
    Incluye regla de dependencia: si es una venta (trinidad), TODAS las acciones
    se bloquean hasta tener datos mínimos de identidad del cliente.
    Retorna (acciones_aprobadas, acciones_bloqueadas, datos_faltantes_texto).
    """
    aprobadas = []
    bloqueadas = []
    faltantes = []

    # =====================================================================
    # REGLA DE DEPENDENCIA: LA TRINIDAD
    # Si estamos creando compañía + persona + oportunidad (venta),
    # NO crear NADA hasta tener al menos nombre del cliente Y empresa.
    # =====================================================================
    acciones_trinidad = {"COMPANIA_CREAR", "PERSONA_CREAR", "OPORTUNIDAD_CREAR"}
    es_venta_completa = acciones_trinidad.issubset(set(acciones))

    if es_venta_completa:
        tiene_nombre = bool(datos.get("nombre_persona"))
        tiene_empresa = bool(datos.get("nombre_empresa"))
        tiene_contacto = bool(datos.get("email")) or bool(datos.get("telefono"))

        if not tiene_nombre or not tiene_empresa or not tiene_contacto:
            # Bloquear TODA la trinidad
            for accion in acciones:
                if accion in acciones_trinidad:
                    bloqueadas.append(accion)
                else:
                    aprobadas.append(accion)

            if not tiene_nombre:
                faltantes.append("tu nombre completo")
            if not tiene_empresa:
                faltantes.append("el nombre de tu empresa o negocio")
            if not tiene_contacto:
                faltantes.append("un correo electrónico o número de teléfono para contactarte")

            return aprobadas, bloqueadas, faltantes

    # =====================================================================
    # VALIDACIÓN INDIVIDUAL (para acciones sueltas o trinidad completa)
    # =====================================================================
    for accion in acciones:
        config = DATOS_REQUERIDOS.get(accion)

        if config is None:
            # Acciones como RESPONDER_FAQ o PERSONA_MODIFICAR no requieren validación
            aprobadas.append(accion)
            continue

        campos_obligatorios = config["campos_obligatorios"]
        tiene_todos = all(datos.get(campo) for campo in campos_obligatorios)

        if tiene_todos:
            aprobadas.append(accion)
        else:
            bloqueadas.append(accion)
            faltantes.append(config["pregunta_faltante"])

    return aprobadas, bloqueadas, faltantes
