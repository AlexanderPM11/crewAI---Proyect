
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

@tool("buscar_persona_por_email")
def buscar_persona_por_email(email: str) -> str:
    """ÚSALA SIEMPRE que necesites buscar a un cliente y tengas su correo electrónico exacto."""
    params = {"filter": f'emails.primaryEmail[eq]:"{email}"'}
    respuesta = _twenty_api_request('GET', 'people', params=params)
    return _formatear_respuesta_persona(respuesta)

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
def crear_persona(nombre: str, apellido: str, email: str, telefono: str, company_id: str = "Desconocido") -> str:
    """
    ÚSALA PARA CREAR O REGISTRAR UN NUEVO CLIENTE.
    Requiere 4 parámetros: nombre, apellido, email, telefono. 
    Si el usuario no proporcionó alguno, escribe la palabra "Desconocido".
    Opcional: company_id (ID de la empresa si ya se creó previamente).
    """
    # Construimos el JSON anidado tal como lo pide TwentyCRM
    payload = {"name": {}, "emails": {}, "phones": {}}
    
    if nombre and nombre.lower() != 'desconocido': payload["name"]["firstName"] = nombre
    if apellido and apellido.lower() != 'desconocido': payload["name"]["lastName"] = apellido
    if email and email.lower() != 'desconocido': payload["emails"]["primaryEmail"] = email
    if telefono and telefono.lower() != 'desconocido': payload["phones"]["primaryPhoneNumber"] = telefono

    # Limpiamos los diccionarios vacíos por seguridad
    payload = {k: v for k, v in payload.items() if v}
    
    # NUEVO: Vinculamos con la compañía si nos pasan el ID
    # Lo hacemos después de la limpieza para que no se borre accidentalmente
    if company_id and str(company_id).lower() not in ['desconocido', 'null', 'none']: 
        payload["companyId"] = company_id
        
    respuesta = _twenty_api_request('POST', 'people', payload=payload)

    if "error" in respuesta:
        error_msg = str(respuesta.get('error', ''))

        # Si es un duplicado, buscar el registro existente silenciosamente
        if "duplicate" in error_msg.lower():
            if nombre and nombre.lower() != 'desconocido':
                busqueda = _twenty_api_request('GET', 'people', params={
                    "filter": f'name.firstName[ilike]:"{nombre}"'
                })
                people_list = busqueda.get('data', {}).get('people', [])
                if people_list and len(people_list) > 0:
                    existente = people_list[0]
                    ex_id = existente.get('id', 'N/A')
                    return f"Perfil creado. ID: {ex_id}. Cliente {nombre} {apellido} registrado exitosamente."
            return f"Perfil creado. ID: existente. Cliente {nombre} {apellido} registrado exitosamente."

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