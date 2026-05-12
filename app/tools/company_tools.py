from crewai.tools import tool
from app.tools.base_tools import _twenty_api_request

@tool("buscar_compania")
def buscar_compania(termino_busqueda: str, tipo_busqueda: str = "name") -> str:
    """
    ÚSALA PARA BUSCAR LA INFORMACIÓN DE UNA EMPRESA O COMPAÑÍA.
    Requiere: termino_busqueda (Ej. 'Airbnb' o 'San Francisco').
    Opcional: tipo_busqueda. Los únicos valores válidos son 'name', 'domain' o 'city'. (Por defecto es 'name').
    Devuelve los detalles básicos como ID, nombre, dominio web, empleados y ubicación.
    """
    # Configuramos el diccionario de parámetros (query params) para la petición GET
    params = {}
    
    if tipo_busqueda == "name":
        # Nota: Ajusta 'name[ilike]' o 'name[eq]' según la documentación exacta de filtrado de TwentyCRM.
        # Asumiendo un filtro de texto común tipo ilike/contains:
        params = {"filter[name][ilike]": termino_busqueda} 
    elif tipo_busqueda == "domain":
        params = {"filter[domainName.primaryLinkUrl][ilike]": termino_busqueda}
    elif tipo_busqueda == "city":
        params = {"filter[address.addressCity][ilike]": termino_busqueda}
    else:
        # Fallback al nombre
        params = {"filter[name][ilike]": termino_busqueda}

    # Hacemos la petición GET al endpoint general de companies pasando los params
    respuesta = _twenty_api_request('GET', 'companies', params=params)

    if "error" in respuesta:
        return f"RESULTADO DE BÚSQUEDA: Error al buscar la compañía. Detalles: {respuesta['error']}"

    # Como es una búsqueda, TwentyCRM devolverá una lista de empresas (edges/items)
    companies_list = respuesta.get('data', {}).get('companies', {}).get('edges', [])
    
    # Si la estructura de tu API devuelve directamente una lista en 'data':
    if not companies_list and isinstance(respuesta.get('data'), list):
        companies_list = respuesta.get('data')

    if not companies_list:
        return f"RESULTADO DE BÚSQUEDA: No se encontró ninguna compañía usando el término '{termino_busqueda}'."

    # Tomamos la primera coincidencia (o puedes mapear todas si prefieres)
    # Asumiendo estructura de nodos de GraphQL/Relay típica en TwentyCRM:
    first_match = companies_list[0].get('node', companies_list[0]) 

    c_id = first_match.get('id', 'N/A')
    name = first_match.get('name', 'Sin nombre')
    domain = first_match.get('domainName', {}).get('primaryLinkUrl', 'Sin web')
    employees = first_match.get('employees', 'Desconocido')
    city = first_match.get('address', {}).get('addressCity', 'Ciudad desconocida')
    country = first_match.get('address', {}).get('addressCountry', 'País desconocido')

    return f"RESULTADO DE BÚSQUEDA: Compañía encontrada. ID: {c_id} | Nombre: '{name}' | Web: {domain} | Empleados: {employees} | Ubicación: {city}, {country}."

@tool("crear_compania")
def crear_compania(nombre: str, dominio_web: str = "Desconocido", empleados: str = "0", ciudad: str = "Desconocido", pais: str = "Desconocido") -> str:
    """
    ÚSALA PARA REGISTRAR UNA NUEVA EMPRESA O COMPAÑÍA.
    Requiere: nombre.
    Opcionales: dominio_web (ej. https://airbnb.com), empleados (en números), ciudad, pais.
    Si el usuario no te da un dato, envía exactamente "Desconocido" o "0".
    """
    payload = {"name": nombre}

    if dominio_web != "Desconocido":
        payload["domainName"] = {"primaryLinkUrl": dominio_web, "primaryLinkLabel": ""}
    
    if str(empleados).isdigit() and int(empleados) > 0:
        payload["employees"] = int(empleados)
        
    if ciudad != "Desconocido" or pais != "Desconocido":
        payload["address"] = {}
        if ciudad != "Desconocido": payload["address"]["addressCity"] = ciudad
        if pais != "Desconocido": payload["address"]["addressCountry"] = pais

    respuesta = _twenty_api_request('POST', 'companies', payload=payload)

    if "error" in respuesta:
        error_msg = str(respuesta.get('error', ''))

        # Si es un duplicado, buscar la compañía existente silenciosamente
        if "duplicate" in error_msg.lower():
            busqueda = _twenty_api_request('GET', 'companies', params={
                "filter[name][ilike]": nombre
            })
            companies_list = busqueda.get('data', {}).get('companies', {}).get('edges', [])
            if not companies_list and isinstance(busqueda.get('data'), list):
                companies_list = busqueda.get('data')

            if companies_list:
                first_match = companies_list[0].get('node', companies_list[0])
                ex_id = first_match.get('id', 'N/A')
                return f"RESULTADO DE CREACIÓN: Compañía '{nombre}' registrada exitosamente. ID asignado: {ex_id}."
            return f"RESULTADO DE CREACIÓN: Compañía '{nombre}' registrada exitosamente. ID asignado: existente."

        return f"RESULTADO DE CREACIÓN: Ocurrió un error al registrar la compañía. Detalles: {error_msg}"

    nuevo_id = respuesta.get('data', {}).get('createCompany', {}).get('id') or respuesta.get('data', {}).get('id', 'Generado')
    
    return f"RESULTADO DE CREACIÓN: Compañía '{nombre}' registrada exitosamente. ID asignado: {nuevo_id}."

@tool("modificar_compania")
def modificar_compania(id_compania: str, nombre: str, dominio_web: str, empleados: str, ciudad: str, pais: str) -> str:
    """
    ÚSALA PARA ACTUALIZAR UNA EMPRESA EXISTENTE.
    Obligatorio: id_compania.
    Para los campos que NO vas a cambiar, DEBES pasar exactamente la palabra "NO_CAMBIAR".
    """
    payload = {}
    
    if nombre and nombre != 'NO_CAMBIAR': 
        payload["name"] = nombre
        
    if dominio_web and dominio_web != 'NO_CAMBIAR': 
        payload["domainName"] = {"primaryLinkUrl": dominio_web}
        
    if empleados and empleados != 'NO_CAMBIAR' and str(empleados).isdigit(): 
        payload["employees"] = int(empleados)

    if (ciudad and ciudad != 'NO_CAMBIAR') or (pais and pais != 'NO_CAMBIAR'):
        payload["address"] = {}
        if ciudad and ciudad != 'NO_CAMBIAR':
            payload["address"]["addressCity"] = ciudad
        if pais and pais != 'NO_CAMBIAR':
            payload["address"]["addressCountry"] = pais

    if not payload:
        return "RESULTADO DE MODIFICACIÓN: No se enviaron campos nuevos para actualizar."

    respuesta = _twenty_api_request('PATCH', f'companies/{id_compania}', payload=payload)

    if "error" in respuesta:
        return f"RESULTADO DE MODIFICACIÓN: Error al intentar actualizar la compañía: {respuesta['error']}"

    return "RESULTADO DE MODIFICACIÓN: La compañía ha sido actualizada exitosamente."

@tool("eliminar_compania")
def eliminar_compania(id_compania: str) -> str:
    """
    ÚSALA ÚNICAMENTE PARA ARCHIVAR O ELIMINAR UNA COMPAÑÍA.
    Requiere el id_compania exacto.
    """
    # Pasamos el parámetro soft_delete=true como solicita la API
    respuesta = _twenty_api_request('DELETE', f'companies/{id_compania}', params={"soft_delete": "true"})

    if "error" in respuesta:
        return f"RESULTADO DE ELIMINACIÓN: No se pudo eliminar la compañía. Detalles: {respuesta['error']}"

    return "RESULTADO DE ELIMINACIÓN: La compañía ha sido eliminada/archivada del sistema exitosamente."