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
                f"2. Extrae datos (¡CRÍTICO!): Escanea TODO el 'HISTORIAL RECIENTE' para encontrar el nombre de la persona, empresa, email, etc.\n"
                f"   - Si el cliente dio su nombre completo (ej: 'Alexander Pérez'), extrae: 'nombre': 'Alexander', 'apellido': 'Pérez'.\n"
                f"   - Si solo dio un nombre (ej: 'Alexander'), deja 'apellido' como 'Desconocido' o intenta inferirlo si hay pistas.\n"
                f"   - Si dijo 'Soy Alexander de Genesa', DEBES extraer: 'nombre': 'Alexander', 'empresa': 'Genesa'.\n"
                f"   - NUNCA dejes campos como 'nombre' o 'empresa' vacíos si están en el historial.\n"
                f"3. Decisión Estratégica:\n"
                f"   - 'EJECUTAR': ¡HAZLO YA! Nuestra prioridad es registrar leads completos.\n"
                f"     Si tienes Nombre y Email, DEBES incluir 'PERSONA_CREAR' en 'acciones_crm'.\n"
                f"     Si además tienes Empresa o Proyecto, añade 'COMPANIA_CREAR' y 'OPORTUNIDAD_CREAR'.\n"
                f"     - ¡IMPORTANTE!: Cada vez que registres una oportunidad o un dato relevante, añade 'NOTA_CREAR' para guardar un resumen cualitativo (preferencias, urgencia, contexto) en el perfil del cliente.\n"
                f"     NUNCA crees una oportunidad sin registrar primero a la PERSONA.\n"
                f"   - 'PEDIR_DATOS': Si falta el Nombre o el Email. Pide máximo 1 o 2 cosas.\n"
                f"   - 'RESPONDER': Solo para saludos o charla sin intención comercial clara.\n\n"
                f"REGLA TÉCNICA: Al pasar datos a los agentes, NO uses estructuras anidadas. Envía los valores planos.\n"
                f"ACCIONES VÁLIDAS: 'PERSONA_CREAR', 'PERSONA_MODIFICAR', 'OPORTUNIDAD_CREAR', 'COMPANIA_CREAR', 'TICKET_CREAR', 'NOTA_CREAR'.\n\n"
                f"RESPONDE ÚNICAMENTE EN JSON:\n"
                f"{{\n"
                f"  \"intencion\": \"resumen\",\n"
                f"  \"acciones_crm\": [\"ACCION_1\", \"ACCION_2\"],\n"
                f"  \"datos_nuevos\": {{}},\n"
                f"  \"datos_faltantes\": [],\n"
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
                f"- Si el Asesor B2B creó una Compañía, busca en el historial el mensaje que dice 'ID asignado: ...'. DEBES usar ese ID técnico (cadena hexadecimal) para el parámetro 'company_id'.\n"
                f"- REGLA DE ORO: NUNCA uses el nombre de la empresa (ej: 'Genesa') como 'company_id'. Si no encuentras un ID técnico con guiones y letras, deja el campo como 'Desconocido'.\n"
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
                f"1. TU ÚNICA MISIÓN ES LLAMAR A LA HERRAMIENTA CORRESPONDIENTE. Si no la usas, HABRÁS FALLADO.\n"
                f"2. NUNCA respondas con un JSON o con texto inventado como 'Final Answer' sin haber recibido una respuesta de la herramienta.\n"
                f"3. NUNCA envíes los datos dentro de un objeto 'properties'. Envía los parámetros directamente (ej: {{\"nombre\": \"valor\"}}).\n"
                f"4. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs."
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
                f"1. TU ÚNICA MISIÓN ES LLAMAR A LA HERRAMIENTA CORRESPONDIENTE. Si no la usas, HABRÁS FALLADO.\n"
                f"2. NUNCA respondas con un JSON o con texto inventado como 'Final Answer' sin haber recibido una respuesta de la herramienta.\n"
                f"3. NUNCA envíes los datos dentro de un objeto 'properties'. Envía los parámetros directamente (ej: {{\"nombre\": \"valor\"}}).\n"
                f"4. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs."
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
                f"- RELACIONES (CRÍTICO): Busca en los mensajes anteriores los IDs técnicos (cadena hexadecimal) generados.\n"
                f"  * Si se creó una Compañía, busca 'ID asignado: ...'. Pásalo a 'company_id'.\n"
                f"  * Si se creó una Persona, busca 'ID: ...' o 'ID asignado: ...'. Pásalo a 'persona_id'.\n"
                f"- REGLA DE ORO: NUNCA uses nombres (ej: 'Alexander' o 'Genesa') como IDs. Si no encuentras el ID técnico, usa 'Desconocido'.\n"
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
                f"1. TU ÚNICA MISIÓN ES LLAMAR A LA HERRAMIENTA CORRESPONDIENTE. Si no la usas, HABRÁS FALLADO.\n"
                f"2. NUNCA respondas con un JSON o con texto inventado como 'Final Answer' sin haber recibido una respuesta de la herramienta.\n"
                f"3. NUNCA envíes los datos dentro de un objeto 'properties'. Envía los parámetros directamente (ej: {{\"nombre\": \"valor\"}}).\n"
                f"4. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs."
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
                f"1. TU ÚNICA MISIÓN ES LLAMAR A LA HERRAMIENTA CORRESPONDIENTE. Si no la usas, HABRÁS FALLADO.\n"
                f"2. NUNCA respondas con un JSON o con texto inventado como 'Final Answer' sin haber recibido una respuesta de la herramienta.\n"
                f"3. NUNCA envíes los datos dentro de un objeto 'properties'. Envía los parámetros directamente (ej: {{\"nombre\": \"valor\"}}).\n"
                f"4. Tu 'Final Answer' DEBE SER EXACTAMENTE LA RESPUESTA LITERAL que te devuelva la herramienta. NO resumas, NO modifiques el texto, NO inventes IDs."
            ),
            expected_output="La respuesta exacta y literal devuelta por la herramienta ejecutada.",
            agent=agente,
            output_json=False
        )

    def tarea_gestionar_nota(self, agente, contexto_chat: str, accion: str, datos_validados: dict):
        """Tarea para crear o gestionar notas en el CRM."""
        return Task(
            description=(
                f"El Gerente de Operaciones te ha pasado este historial:\n"
                f"--- INICIO ---\n{contexto_chat}\n--- FIN ---\n\n"
                f"ACCIÓN: {accion}.\n\n"
                f"DATOS RELEVANTES: {json.dumps(datos_validados, ensure_ascii=False)}\n\n"
                f"REGLAS PARA LA NOTA:\n"
                f"1. Redacta un 'RESUMEN EJECUTIVO' de la charla. No copies todo, extrae lo valioso.\n"
                f"2. Incluye: Necesidad principal, Empresa/Proyecto, Urgencia detectada y cualquier preferencia mencionada.\n"
                f"3. Vincula la nota usando el 'person_id' (¡PRIORIDAD!) o 'company_id' que encuentres en el historial (IDs técnicos hexadecimales).\n"
                f"4. Tu 'Final Answer' DEBE SER LA RESPUESTA LITERAL de la herramienta."
            ),
            expected_output="Confirmación de la creación de la nota.",
            agent=agente
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
                f"1. Eres un Asesor de Triple Tecnología (equipo corporativo). NO inventes un nombre para ti (ej: No digas 'Soy Sofía').\n"
                f"   Personaliza la respuesta usando el nombre del cliente: {nombre_cliente}.\n"
                f"2. CONFIRMACIÓN: Si el 'Reporte CRM' dice que se crearon registros, menciónalo (ej: 'Ya registré tu proyecto de {datos_acumulados.get('nombre_proyecto', 'software')}').\n"
                f"3. SI el cliente pide información, usa 'leer_faqs_empresa' con {{\"tema\": \"...\"}}.\n"
                f"4. Responde de forma cálida y breve (máximo 3 frases).\n"
                f"5. {instruccion_datos}\n"
                f"6. REGLA CRÍTICA: Tu salida final debe ser SOLO el mensaje para el cliente. Sin 'Thought' ni 'Action'."
            ),
            expected_output="El mensaje final que el cliente recibirá por WhatsApp.",
            agent=agente
        )