import json
from crewai import Task


class TareasDepartamentoCRM:

    def tarea_maestra_jerarquica(self, mensaje_usuario: str):
        """Tarea global que el Manager analizará para delegar a los especialistas."""
        return Task(
            description=(
                f"Atiende la siguiente solicitud del cliente: '{mensaje_usuario}'.\n\n"
                f"Eres el Gerente de Operaciones del CRM. Debes analizar la solicitud y delegar el trabajo a tus especialistas "
                f"según sea necesario. Si la solicitud implica múltiples pasos (ej. un prospecto nuevo quiere cotizar: debes pedirle "
                f"al Asesor B2B que registre su empresa, luego al Especialista en Personas que lo registre a él, y luego al Ejecutivo de Ventas "
                f"que cree la oportunidad de venta), debes coordinar a los agentes secuencialmente para que lo hagan.\n\n"
                f"Tus especialistas disponibles son:\n"
                f"- Especialista en Atención al Cliente (maneja Personas individuales)\n"
                f"- Asesor Corporativo B2B (maneja Compañías)\n"
                f"- Ejecutivo de Ventas (maneja Oportunidades comerciales)\n"
                f"- Ingeniero de Soporte (maneja Tickets técnicos)\n\n"
                f"Asegúrate de que completen sus tareas usando herramientas. "
                f"Al final, redacta una respuesta conversacional y amable en primera persona ('yo') directamente para el cliente, "
                f"resumiendo y confirmando todo lo que tu equipo registró en el sistema (menciona los IDs si es útil)."
            ),
            expected_output="Una respuesta amable y profesional en primera persona confirmando todas las acciones realizadas en el CRM.",
        )

    def tarea_enrutamiento(self, agente, mensaje_usuario: str):
        return Task(
            description=f"Analiza la intención principal de este mensaje: '{mensaje_usuario}'...",
            expected_output='Una sola palabra clave.',
            agent=agente,
            output_json=False
        )

    def tarea_gestionar_persona(self, agente, mensaje_usuario: str, accion_detectada: str, datos_validados: dict = None):
        """Tarea para el Agente de Personas (Modo Back-office)."""
        datos_validados = datos_validados or {}

        if accion_detectada == "PERSONA_MODIFICAR":
            reglas_especificas = (
                f"REGLAS PARA MODIFICAR:\n"
                f"- PASO 1 (CRÍTICO): Lee la '[Memoria Interna CRM]' en los mensajes de arriba. Busca la frase exacta que dice 'Perfil creado. ID: ...' y extrae ESE ID exacto.\n"
                f"- PASO 2: Usa la herramienta 'modificar_persona' pasándole ese ID.\n"
                f"- REGLA DE TELÉFONO: Si el número es de RD (809, 829, 849), agrega '+1' (Ej. +18095551234).\n\n"
                f"DATOS CONFIRMADOS DEL CLIENTE (usa SOLO estos):\n"
                f"{json.dumps(datos_validados, ensure_ascii=False, indent=2)}"
            )
        else:
            reglas_especificas = (
                f"REGLAS PARA CREAR:\n"
                f"- DATOS CONFIRMADOS DEL CLIENTE (usa SOLO estos, NO inventes datos adicionales):\n"
                f"{json.dumps(datos_validados, ensure_ascii=False, indent=2)}\n\n"
                f"- MAPEO DE CAMPOS:\n"
                f"  * nombre_persona → parámetro 'nombre'\n"
                f"  * apellido → parámetro 'apellido'\n"
                f"  * email → parámetro 'email'\n"
                f"  * telefono → parámetro 'telefono'\n\n"
                f"- Si un campo NO aparece en los datos confirmados, usa 'Desconocido'.\n"
                f"- REGLA DE TELÉFONO: Si es de RD (809, 829, 849), agrega '+1'. NUNCA uses '+809'.\n"
                f"- Si el Asesor B2B creó una Compañía, extrae su ID del historial y pásalo a 'company_id'.\n"
                f"- PROHIBIDO: Inventar emails, teléfonos o nombres que NO estén en los datos confirmados."
            )

        return Task(
            description=(
                f"El Gerente de Operaciones te ha pasado este historial de conversación:\n"
                f"--- INICIO HISTORIAL ---\n{mensaje_usuario}\n--- FIN HISTORIAL ---\n\n"
                f"La acción que debes ejecutar en la base de datos es: {accion_detectada}.\n\n"
                f"{reglas_especificas}\n\n"
                f"REGLA DE PERSPECTIVA:\n"
                f"- NO estás hablando con el cliente. Le estás reportando a tu Gerente.\n\n"
                f"REGLA DE EJECUCIÓN (¡OBLIGATORIA!):\n"
                f"1. Ejecuta la herramienta correspondiente usando ÚNICAMENTE los datos confirmados.\n"
                f"2. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs. Copia y pega el resultado de la herramienta."
            ),
            expected_output="La respuesta exacta y literal devuelta por la herramienta ejecutada.",
            agent=agente,
            output_json=False
        )

    def tarea_gestionar_ticket(self, agente, mensaje_usuario: str, accion_detectada: str, datos_validados: dict = None):
        """Tarea para el Agente de Tickets (Modo Back-office)."""
        datos_validados = datos_validados or {}

        if accion_detectada == "TICKET_CREAR":
            reglas_especificas = (
                f"- DATOS CONFIRMADOS DEL CLIENTE (usa SOLO estos):\n"
                f"{json.dumps(datos_validados, ensure_ascii=False, indent=2)}\n\n"
                f"- Usa 'descripcion_problema' como descripción del ticket.\n"
                f"- Inventa un título breve basado en la descripción y usa estado 'TODO'.\n"
                f"- PROHIBIDO: Inventar descripciones que el cliente no haya reportado."
            )
        else:
            reglas_especificas = f"- Envía la palabra 'NO_CAMBIAR' en los parámetros que no se tocan."

        return Task(
            description=(
                f"El Gerente de Operaciones te ha pasado este historial de conversación:\n"
                f"--- INICIO HISTORIAL ---\n{mensaje_usuario}\n--- FIN HISTORIAL ---\n\n"
                f"La acción requerida es: {accion_detectada}.\n\n"
                f"REGLAS ESTRICTAS:\n{reglas_especificas}\n\n"
                f"REGLA DE PERSPECTIVA:\n"
                f"- NO estás hablando con el cliente. Le estás reportando a tu Gerente.\n\n"
                f"REGLA DE EJECUCIÓN (¡OBLIGATORIA!):\n"
                f"1. Ejecuta la herramienta correspondiente usando ÚNICAMENTE los datos confirmados.\n"
                f"2. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs. Copia y pega el resultado de la herramienta."
            ),
            expected_output="La respuesta exacta y literal devuelta por la herramienta ejecutada.",
            agent=agente,
            output_json=False
        )

    def tarea_gestionar_oportunidad(self, agente, mensaje_usuario: str, accion_detectada: str, datos_validados: dict = None):
        """Tarea para el Agente de Ventas (Modo Back-office)."""
        datos_validados = datos_validados or {}

        if accion_detectada == "OPORTUNIDAD_CREAR":
            reglas_especificas = (
                f"REGLAS PARA CREAR:\n"
                f"- DATOS CONFIRMADOS DEL CLIENTE (usa SOLO estos, NO inventes datos adicionales):\n"
                f"{json.dumps(datos_validados, ensure_ascii=False, indent=2)}\n\n"
                f"- MAPEO DE CAMPOS:\n"
                f"  * nombre_proyecto → parámetro 'nombre'\n"
                f"  * presupuesto → parámetro 'monto' (número SIN comas, Ej. 60000)\n\n"
                f"- Si 'presupuesto' no está en los datos, usa 0.\n"
                f"- Usa la etapa 'NEW' por defecto.\n"
                f"- RELACIONES: Revisa los mensajes anteriores. Si tus compañeros ya crearon una Compañía y una Persona, copia ESOS IDs exactos y pásalos a 'company_id' y 'persona_id'.\n"
                f"- PROHIBIDO: Inventar nombres de proyecto o montos que el cliente no haya mencionado."
            )
        else:
            reglas_especificas = (
                f"REGLAS PARA MODIFICAR:\n"
                f"- Usa solo las etapas válidas: 'NEW', 'SCREENING', 'MEETING', 'PROPOSAL', 'CUSTOMER'."
            )

        return Task(
            description=(
                f"El Gerente de Operaciones te ha pasado este historial de conversación:\n"
                f"--- INICIO HISTORIAL ---\n{mensaje_usuario}\n--- FIN HISTORIAL ---\n\n"
                f"La acción requerida es: {accion_detectada}.\n\n"
                f"{reglas_especificas}\n\n"
                f"REGLA DE PERSPECTIVA:\n"
                f"- NO estás hablando con el cliente. Le estás reportando a tu Gerente.\n\n"
                f"REGLA DE EJECUCIÓN (¡OBLIGATORIA!):\n"
                f"1. Ejecuta la herramienta correspondiente usando ÚNICAMENTE los datos confirmados.\n"
                f"2. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs. Copia y pega el resultado de la herramienta."
            ),
            expected_output="La respuesta exacta y literal devuelta por la herramienta ejecutada.",
            agent=agente,
            output_json=False
        )

    def tarea_gestionar_compania(self, agente, mensaje_usuario: str, accion_detectada: str, datos_validados: dict = None):
        """Tarea para el Agente B2B (Modo Back-office)."""
        datos_validados = datos_validados or {}

        if accion_detectada == "COMPANIA_CREAR":
            reglas_especificas = (
                f"- DATOS CONFIRMADOS DEL CLIENTE (usa SOLO estos, NO inventes datos adicionales):\n"
                f"{json.dumps(datos_validados, ensure_ascii=False, indent=2)}\n\n"
                f"- MAPEO DE CAMPOS:\n"
                f"  * nombre_empresa → parámetro 'nombre'\n"
                f"  * dominio_web → parámetro 'dominio_web'\n"
                f"  * empleados → parámetro 'empleados'\n"
                f"  * ciudad → parámetro 'ciudad'\n"
                f"  * pais → parámetro 'pais'\n\n"
                f"- Si un campo NO aparece en los datos confirmados, usa 'Desconocido' o '0'.\n"
                f"- PROHIBIDO: Inventar nombres de empresa, dominios web o ubicaciones."
            )
        else:
            reglas_especificas = f"- Si modificas, envía 'NO_CAMBIAR' a los parámetros que se quedan igual."

        return Task(
            description=(
                f"El Gerente de Operaciones te ha pasado este historial de conversación:\n"
                f"--- INICIO HISTORIAL ---\n{mensaje_usuario}\n--- FIN HISTORIAL ---\n\n"
                f"La acción requerida es: {accion_detectada}.\n\n"
                f"REGLAS ESTRICTAS:\n{reglas_especificas}\n\n"
                f"REGLA DE PERSPECTIVA:\n"
                f"- NO estás hablando con el cliente. Le estás reportando a tu Gerente.\n\n"
                f"REGLA DE EJECUCIÓN (¡OBLIGATORIA!):\n"
                f"1. Ejecuta la herramienta correspondiente usando ÚNICAMENTE los datos confirmados.\n"
                f"2. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs. Copia y pega el resultado de la herramienta."
            ),
            expected_output="La respuesta exacta y literal devuelta por la herramienta ejecutada.",
            agent=agente,
            output_json=False
        )