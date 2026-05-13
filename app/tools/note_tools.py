from crewai.tools import tool
from app.tools.base_tools import _twenty_api_request

@tool("crear_nota")
def crear_nota(contenido: str = "", persona_id: str = "", company_id: str = "", opportunity_id: str = "", **kwargs) -> str:
    """
    Crea una nota o comentario.
    Parámetros: contenido, persona_id, company_id, opportunity_id.
    """
    # FAIL-SAFE para errores de estructura del LLM
    data = kwargs
    if not contenido and 'properties' in kwargs:
        data = kwargs['properties']
        contenido = data.get('contenido')
        persona_id = data.get('persona_id', persona_id)
        company_id = data.get('company_id', company_id)
        opportunity_id = data.get('opportunity_id', opportunity_id)

    contenido = contenido or kwargs.get('contenido')
    if not contenido:
        return "Error: El contenido de la nota es obligatorio."

    payload = {"body": contenido}
    
    import re
    def is_uuid(val):
        if not val or str(val).lower() in ['desconocido', 'null', 'none', '']: return False
        return bool(re.match(r'^[0-9a-fA-F-]+$', str(val)) and len(str(val)) > 20)

    # Vinculamos la nota a la entidad correspondiente
    if is_uuid(persona_id): payload["personId"] = persona_id
    if is_uuid(company_id): payload["companyId"] = company_id
    if is_uuid(opportunity_id): payload["opportunityId"] = opportunity_id
        
    respuesta = _twenty_api_request('POST', 'notes', payload=payload)
    
    if "error" in respuesta:
        # Si falla por el nombre del campo, intentamos con un esquema genérico o devolvemos el error
        return f"Error al crear la nota en el CRM. Detalles: {respuesta['error']}"
        
    return "La nota ha sido guardada exitosamente en el historial del cliente."

@tool("buscar_notas_por_persona")
def buscar_notas_por_persona(persona_id: str) -> str:
    """
    ÚSALA PARA CONSULTAR EL HISTORIAL DE NOTAS O COMENTARIOS DE UN CLIENTE ESPECÍFICO.
    Requiere el persona_id.
    """
    params = {"filter": f'personId[eq]:"{persona_id}"'}
    respuesta = _twenty_api_request('GET', 'notes', params=params)
    
    if "error" in respuesta:
        return f"No se pudieron recuperar las notas. Detalles: {respuesta['error']}"
        
    notas = respuesta.get('data', {}).get('notes', [])
    if not notas:
        return "No hay notas previas registradas para este cliente."
        
    resumen = "\n".join([f"- {n.get('body', '')}" for n in notas])
    return f"NOTAS ENCONTRADAS:\n{resumen}"
