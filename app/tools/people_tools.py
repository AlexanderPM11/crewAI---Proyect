
import os
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# Cargar función base
from app.tools.base_tools import _twenty_api_request

# Cargar variables de entorno
load_dotenv()

def _formatear_respuesta_persona(data_json: dict) -> str:
    """Parsea el JSON de TwentyCRM y formatea la orden final."""
    if "error" in data_json:
        return f"Final Answer: Ocurrió un error al consultar la base de datos: {data_json['error']}"
        
    people_list = data_json.get('data', {}).get('people', [])
    
    if people_list and len(people_list) > 0:
        contact = people_list[0]
        c_id = contact.get('id', 'N/A')
        f_name = contact.get('name', {}).get('firstName', '')
        l_name = contact.get('name', {}).get('lastName', '')
        
        # EL CAMBIO: Extraemos el teléfono, pero evitamos palabras negativas
        phone_raw = contact.get('phones', {}).get('primaryPhoneNumber')
        
        if phone_raw:
            texto_telefono = f"Su teléfono de contacto es {phone_raw}."
        else:
            texto_telefono = "Actualmente no tiene un número de teléfono guardado en su perfil."
        
        # Redactamos el texto resaltando en mayúsculas que SÍ EXISTE
        return f"¡Hola! He verificado exitosamente y el cliente {f_name} {l_name} SÍ EXISTE en nuestra base de datos. Su ID interno es {c_id}. Y su teléfono es {texto_telefono}"
        
    else:
        return "RESULTADO: El cliente no existe en la base de datos."
# ==========================================
# HERRAMIENTAS PARA MANEJO DE CONTACTOS
# ==========================================

def _buscar_persona_por_email_logic(email: str, nombre: str = "") -> str:
    """Lógica interna de búsqueda con fallback por nombre."""
    if not email or email.lower() == 'desconocido':
        return "No se proporcionó un email válido."
        
    # Intento 1: Por Email exacto
    params = {"filter": f'emails.primaryEmail[eq]:"{email}"'}
    respuesta = _twenty_api_request('GET', 'people', params=params)
    people = respuesta.get('data', {}).get('people', [])
    
    # Intento 2: Si no hay resultados y tenemos nombre, buscar por nombre
    if not people and nombre and nombre.lower() != 'desconocido':
        params_name = {"filter": f'name.firstName[ilike]:"{nombre}"'}
        respuesta = _twenty_api_request('GET', 'people', params=params_name)
        people = respuesta.get('data', {}).get('people', [])

    if not people:
        return f"No se encontró ninguna persona."
    
    p = people[0]
    p_id = p.get('id', 'N/A')
    p_email = p.get('emails', {}).get('primaryEmail', email)
    name = p.get('name', {})
    full_name = f"{name.get('firstName', '')} {name.get('lastName', '')}".strip()
    
    return f"Persona encontrada. ID: {p_id} | Nombre: {full_name} | Email: {p_email}"

@tool("buscar_persona_por_email")
def buscar_persona_por_email(email: str) -> str:
    """
    Busca una persona en el CRM usando su correo electrónico.
    Úsala para verificar si un cliente ya existe antes de crearlo.
    """
    return _buscar_persona_por_email_logic(email)

@tool("buscar_persona_por_nombre")
def buscar_persona_por_nombre(nombre: str) -> str:
    """ÚSALA para buscar a un cliente si SOLO tienes su primer nombre (Ej. 'Brian')."""
    # Usamos [ilike] en lugar de [eq] para que ignore mayúsculas/minúsculas
    params = {"filter": f'name.firstName[ilike]:"{nombre}"'}
    respuesta = _twenty_api_request('GET', 'people', params=params)
    return _formatear_respuesta_persona(respuesta)

@tool("buscar_persona_por_apellido")
def buscar_persona_por_apellido(apellido: str) -> str:
    """ÚSALA para buscar a un cliente si SOLO tienes su apellido (Ej. 'Chesky')."""
    params = {"filter": f'name.lastName[ilike]:"{apellido}"'}
    respuesta = _twenty_api_request('GET', 'people', params=params)
    return _formatear_respuesta_persona(respuesta)

@tool("buscar_persona_por_telefono")
def buscar_persona_por_telefono(telefono: str) -> str:
    """ÚSALA para buscar a un cliente si SOLO tienes su número de teléfono."""
    params = {"filter": f'phones.primaryPhoneNumber[eq]:"{telefono}"'}
    respuesta = _twenty_api_request('GET', 'people', params=params)
    return _formatear_respuesta_persona(respuesta)

@tool("crear_persona")
def crear_persona(nombre: str = "", apellido: str = "", email: str = "", telefono: str = "", company_id: str = "Desconocido", **kwargs) -> str:
    """
    Crea un nuevo cliente.
    Parámetros: nombre, apellido, email, telefono, company_id.
    """
    # FAIL-SAFE para errores de estructura del LLM (propiedades anidadas)
    data = kwargs
    if not nombre and 'properties' in kwargs:
        data = kwargs['properties']
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        email = data.get('email')
        telefono = data.get('telefono')
        company_id = data.get('company_id', company_id)

    # Si no vinieron en properties, buscamos en los argumentos directos o kwargs
    nombre = nombre or kwargs.get('nombre')
    apellido = apellido or kwargs.get('apellido')
    email = email or kwargs.get('email')
    telefono = telefono or kwargs.get('telefono')

    if not nombre:
        return "Error: El nombre es obligatorio para crear una persona."
    
    # Si falta el apellido, no bloqueamos, usamos 'Desconocido'
    if not apellido or str(apellido).lower() in ['none', 'null', '']:
        apellido = "Desconocido"

    # Construimos el JSON anidado tal como lo pide TwentyCRM
    payload = {"name": {}, "emails": {}, "phones": {}}
    
    if nombre and nombre.lower() != 'desconocido': payload["name"]["firstName"] = nombre
    if apellido and apellido.lower() != 'desconocido': payload["name"]["lastName"] = apellido
    if email and email.lower() != 'desconocido': payload["emails"]["primaryEmail"] = email
    if telefono and telefono.lower() != 'desconocido': payload["phones"]["primaryPhoneNumber"] = telefono

    # Limpiamos los diccionarios vacíos por seguridad
    payload = {k: v for k, v in payload.items() if v}
    
    # NUEVO: Vinculamos con la compañía si nos pasan el ID
    # VALIDACIÓN DE UUID: Solo enviamos si parece un ID real, no un nombre (como 'Genesa')
    import re
    is_valid_uuid = False
    if company_id and str(company_id).lower() not in ['desconocido', 'null', 'none']:
        # Un UUID suele tener guiones o ser una cadena larga hexadecimal. 
        # Si tiene espacios o es muy corto, probablemente sea un nombre.
        if re.match(r'^[0-9a-fA-F-]+$', str(company_id)) and len(str(company_id)) > 20:
            is_valid_uuid = True
            
    if is_valid_uuid: 
        payload["companyId"] = company_id
        
    respuesta = _twenty_api_request('POST', 'people', payload=payload)

    if "error" in respuesta:
        error_msg = str(respuesta.get('error', ''))

        # Si es un duplicado, buscar el registro existente silenciosamente
        if "duplicate" in error_msg.lower():
            # PASO 1: Verificar si ya existe para evitar duplicados
            existente_msg = _buscar_persona_por_email_logic(email, nombre=nombre)
            if "encontrada" in existente_msg.lower():
                # Extraemos el ID real (UUID) de la respuesta de búsqueda
                import re
                match = re.search(r"ID: ([a-f0-9-]{36})", existente_msg)
                if match:
                    persona_id_real = match.group(1)
                    return f"Cliente ya registrado anteriormente. ID: {persona_id_real}. (Se usará este ID para las vinculaciones)."
                else:
                    return f"Error: Se encontró al cliente pero no se pudo extraer su ID técnico de: {existente_msg}"

        return f"Ocurrió un error al intentar registrar al cliente. Detalles: {error_msg}"

    nuevo_id = respuesta.get('data', {}).get('createPerson', {}).get('id') or respuesta.get('data', {}).get('id', 'Generado exitosamente')
    
    return f"Perfil creado. ID: {nuevo_id}. Cliente {nombre} {apellido} registrado exitosamente."

@tool("modificar_persona")
def modificar_persona(id_persona: str, nombre: str = "NO_CAMBIAR", apellido: str = "NO_CAMBIAR", email: str = "NO_CAMBIAR", telefono: str = "NO_CAMBIAR") -> str:
    """
    ÚSALA PARA ACTUALIZAR O MODIFICAR LOS DATOS DE UN CLIENTE EXISTENTE.
    Obligatorio: id_persona (Ej. a2e78a5e-...).
    Para los campos que NO vas a cambiar, DEBES pasar exactamente la palabra "NO_CAMBIAR".
    """
    payload = {"name": {}, "emails": {}, "phones": {}}
    
    if nombre and nombre != 'NO_CAMBIAR': payload["name"]["firstName"] = nombre
    if apellido and apellido != 'NO_CAMBIAR': payload["name"]["lastName"] = apellido
    if email and email != 'NO_CAMBIAR': payload["emails"]["primaryEmail"] = email
    if telefono and telefono != 'NO_CAMBIAR': payload["phones"]["primaryPhoneNumber"] = telefono

    payload = {k: v for k, v in payload.items() if v}

    # El PATCH se envía al endpoint people/{id}
    respuesta = _twenty_api_request('PATCH', f'people/{id_persona}', payload=payload)

    if "error" in respuesta:
        return f" Ocurrió un error al intentar actualizar los datos: {respuesta['error']}"

    return f"¡Hecho! Los datos del cliente han sido actualizados exitosamente en la base de datos."

@tool("eliminar_persona")
def eliminar_persona(id_persona: str) -> str:
    """
    ÚSALA ÚNICAMENTE PARA BORRAR O ELIMINAR A UN CLIENTE.
    Requiere el id_persona exacto.
    """
    respuesta = _twenty_api_request('DELETE', f'people/{id_persona}')

    if "error" in respuesta:
        return f"No se pudo eliminar el registro. Detalles: {respuesta['error']}"

    return f"El perfil del cliente ha sido eliminado permanentemente del sistema."