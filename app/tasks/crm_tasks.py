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

    def tarea_analisis_estrategico(self, agente, mensaje_usuario: str, contexto_chat: str, datos_acumulados: dict):
        return Task(
            description=(
                f"Analiza la situación actual de esta conversación:\n"
                f"--- HISTORIAL RECIENTE ---\n{contexto_chat}\n\n"
                f"--- ÚLTIMO MENSAJE ---\n'{mensaje_usuario}'\n\n"
                f"--- DATOS QUE YA TENEMOS ---\n{json.dumps(datos_acumulados, ensure_ascii=False)}\n\n"
                f"TU MISIÓN:\n"
                f"1. Identifica la intención: ¿Qué quiere el cliente? (Saber precios, soporte, cotizar, saludar, etc.).\n"
                f"2. Extrae datos: Captura cualquier información nueva (nombre, email, proyecto, etc.).\n"
                f"3. Prioriza Faltantes: Si es un lead nuevo, los datos CRÍTICOS son 'nombre_persona' y 'email'.\n"
                f"   No listes todos los campos posibles; solo los 2-3 más importantes para el siguiente paso.\n"
                f"4. Toma una decisión estratégica: \n"
                f"   - 'EJECUTAR': Solo si tienes Nombre, Email y al menos una idea del Proyecto.\n"
                f"   - 'PEDIR_DATOS': Si falta el Nombre o el Email para poder registrarlo.\n"
                f"   - 'RESPONDER': Si es solo un saludo o charla informal sin intención comercial clara aún.\n\n"
                f"RESPONDE ÚNICAMENTE EN JSON:\n"
                f"{{\n"
                f"  \"intencion\": \"resumen\",\n"
                f"  \"acciones_crm\": [],\n"
                f"  \"datos_nuevos\": {{}},\n"
                f"  \"datos_faltantes\": [\"solo los 2 más urgentes\"],\n"
                f"  \"decision\": \"EJECUTAR | PEDIR_DATOS | RESPONDER\"\n"
                f"}}"
            ),
            expected_output="Un JSON estructurado con la estrategia a seguir.",
            agent=agente
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
                f"  * presupuesto → parámetro 'monto' (número SIN comas, Ej. 60000)\n"
                f"  * descripcion_proyecto + fecha_cita (ej: Jueves 2pm) → parámetro 'descripcion'\n\n"
                f"- Si 'presupuesto' no está en los datos, usa 0.\n"
                f"- Usa la etapa 'NEW' por defecto, a menos que ya se esté coordinando una reunión ('fecha_cita' presente), en cuyo caso usa 'SCREENING'.\n"
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

    def tarea_respuesta_final(self, agente, mensaje_usuario: str, reporte_backoffice: str, datos_faltantes: list, contexto_chat: str, datos_acumulados: dict):
        """Tarea para generar la respuesta final al cliente."""
        
        datos_a_pedir = datos_faltantes[:2]
        instruccion_datos = ""
        if datos_a_pedir:
            instruccion_datos = f"Al final, solicita amablemente SOLO estos datos: {', '.join(datos_a_pedir)}."
        
        # Extraer nombre si existe para personalizar
        nombre_cliente = datos_acumulados.get('nombre_persona', '')
        saludo_personalizado = f"Hola {nombre_cliente}," if nombre_cliente else "¡Hola!"

        return Task(
            description=(
                f"SITUACIÓN:\n"
                f"- Mensaje Cliente: '{mensaje_usuario}'\n"
                f"- Datos conocidos: {json.dumps(datos_acumulados, ensure_ascii=False)}\n"
                f"- Reporte CRM: {reporte_backoffice}\n\n"
                f"TU MISIÓN:\n"
                f"1. Eres un Asesor Humano de Triple Tecnología. Usa los datos conocidos para personalizar (ej: usa el nombre {nombre_cliente}).\n"
                f"2. SI el cliente pide información (servicios, productos, precios), usa 'leer_faqs_empresa'.\n"
                f"   IMPORTANTE: El input de la herramienta debe ser un JSON simple, ej: {{\"tema\": \"servicios\"}}. NO uses 'properties'.\n"
                f"3. Responde de forma cálida, profesional y breve (máximo 3 frases).\n"
                f"4. {instruccion_datos}\n"
                f"5. REGLA CRÍTICA: Tu salida final debe ser SOLO el mensaje para el cliente. Sin etiquetas 'Thought' ni 'Action'."
            ),
            expected_output="El mensaje final que el cliente recibirá por WhatsApp.",
            agent=agente
        )