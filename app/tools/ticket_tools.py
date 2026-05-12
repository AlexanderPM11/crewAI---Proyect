from crewai.tools import tool
from app.tools.base_tools import _twenty_api_request

@tool("buscar_ticket")
def buscar_ticket(id_ticket: str) -> str:
    """
    ÚSALA PARA BUSCAR LA INFORMACIÓN DE UN TICKET O TAREA.
    Requiere 1 parámetro obligatorio: id_ticket (el UUID del ticket).
    Devuelve los detalles del ticket, su estado actual y su descripción.
    """
    respuesta = _twenty_api_request('GET', f'tasks/{id_ticket}')

    if "error" in respuesta:
        return f"RESULTADO DE BÚSQUEDA: Error al buscar el ticket. Detalles: {respuesta['error']}"

    task_data = respuesta.get('data', {}).get('task', {})
    
    if not task_data:
        return "RESULTADO DE BÚSQUEDA: El ticket no existe o fue eliminado."

    t_id = task_data.get('id', 'N/A')
    title = task_data.get('title', 'Sin título')
    status = task_data.get('status', 'DESCONOCIDO')
    
    # Extraemos la descripción manejando la estructura bodyV2
    body = task_data.get('bodyV2', {})
    descripcion = body.get('markdown', 'Sin descripción') if body else 'Sin descripción'

    return f"RESULTADO DE BÚSQUEDA: Ticket encontrado. ID: {t_id} | Título: '{title}' | Estado: {status} | Descripción: '{descripcion.strip()}'"

@tool("crear_ticket")
def crear_ticket(titulo: str, descripcion: str, estado: str = "TODO") -> str:
    """
    ÚSALA PARA CREAR O ABRIR UN NUEVO TICKET/TAREA DE SOPORTE.
    Requiere: titulo, descripcion.
    Opcional: estado. LOS ÚNICOS ESTADOS VÁLIDOS SON EXACTAMENTE: "TODO", "IN_PROGRESS", o "DONE". 
    NUNCA uses palabras en español para el estado.    """
    payload = {
        "title": titulo,
        "status": estado,
        "bodyV2": {
            "blocknote": None,
            "markdown": descripcion
        }
    }

    respuesta = _twenty_api_request('POST', 'tasks', payload=payload)

    if "error" in respuesta:
        return f"RESULTADO DE CREACIÓN: Ocurrió un error al crear el ticket. Detalles: {respuesta['error']}"

    # Extraemos el ID del nuevo ticket
    nuevo_id = respuesta.get('data', {}).get('createTask', {}).get('id') or respuesta.get('data', {}).get('id', 'Generado exitosamente')
    
    return f"RESULTADO DE CREACIÓN: Ticket creado exitosamente. El ID asignado es {nuevo_id} y su estado inicial es {estado}."

@tool("modificar_ticket")
def modificar_ticket(id_ticket: str, titulo: str, descripcion: str, estado: str) -> str:
    """
    ÚSALA PARA ACTUALIZAR O MODIFICAR UN TICKET EXISTENTE.
    Obligatorio: id_ticket.
    IMPORTANTE: LOS ÚNICOS ESTADOS VÁLIDOS SON EXACTAMENTE: "TODO" (Por hacer), "IN_PROGRESS" (En progreso), o "DONE" (Resuelto/Completado).
    NUNCA uses la palabra 'Resuelto' en la herramienta, usa siempre 'DONE'.
    Para los campos que NO vas a cambiar, DEBES pasar exactamente la palabra "NO_CAMBIAR".    """
    payload = {}
    
    if titulo and titulo != 'NO_CAMBIAR': 
        payload["title"] = titulo
    if estado and estado != 'NO_CAMBIAR': 
        payload["status"] = estado
    if descripcion and descripcion != 'NO_CAMBIAR': 
        payload["bodyV2"] = {
            "blocknote": None,
            "markdown": descripcion
        }

    if not payload:
        return "RESULTADO DE MODIFICACIÓN: No se enviaron campos nuevos para actualizar."

    respuesta = _twenty_api_request('PATCH', f'tasks/{id_ticket}', payload=payload)

    if "error" in respuesta:
        return f"RESULTADO DE MODIFICACIÓN: Error al intentar actualizar el ticket: {respuesta['error']}"

    return "RESULTADO DE MODIFICACIÓN: El ticket ha sido actualizado exitosamente."

@tool("eliminar_ticket")
def eliminar_ticket(id_ticket: str) -> str:
    """
    ÚSALA ÚNICAMENTE PARA BORRAR, CANCELAR O ELIMINAR UN TICKET PERMANENTEMENTE.
    Requiere el id_ticket exacto.
    """
    respuesta = _twenty_api_request('DELETE', f'tasks/{id_ticket}')

    if "error" in respuesta:
        return f"RESULTADO DE ELIMINACIÓN: No se pudo eliminar el ticket. Detalles: {respuesta['error']}"

    return "RESULTADO DE ELIMINACIÓN: El ticket ha sido eliminado permanentemente del sistema."