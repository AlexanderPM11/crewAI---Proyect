from crewai.tools import tool
from app.tools.base_tools import _twenty_api_request

@tool("buscar_oportunidad")
def buscar_oportunidad(id_oportunidad: str) -> str:
    """
    ÚSALA PARA BUSCAR LA INFORMACIÓN DE UNA OPORTUNIDAD DE VENTA.
    Requiere 1 parámetro obligatorio: id_oportunidad (el UUID de la oportunidad).
    Devuelve los detalles, el monto y la etapa de la oportunidad.
    """
    respuesta = _twenty_api_request('GET', f'opportunities/{id_oportunidad}')

    if "error" in respuesta:
        return f"RESULTADO DE BÚSQUEDA: Error al buscar la oportunidad. Detalles: {respuesta['error']}"

    opp_data = respuesta.get('data', {}).get('opportunity', {})
    
    if not opp_data:
        return "RESULTADO DE BÚSQUEDA: La oportunidad no existe en la base de datos."

    o_id = opp_data.get('id', 'N/A')
    name = opp_data.get('name', 'Sin nombre')
    stage = opp_data.get('stage', 'DESCONOCIDO')
    
    # Manejamos los micros para devolverle al agente un número normal
    amount_data = opp_data.get('amount', {})
    micros = amount_data.get('amountMicros', 0)
    currency = amount_data.get('currencyCode', 'USD')
    monto_real = float(micros) / 1000000 if micros else 0.0

    return f"RESULTADO DE BÚSQUEDA: Oportunidad encontrada. ID: {o_id} | Nombre: '{name}' | Etapa: {stage} | Monto: {monto_real} {currency}"

@tool("crear_oportunidad")
def crear_oportunidad(nombre: str, monto: str = "0", moneda: str = "USD", etapa: str = "NEW", company_id: str = "Desconocido", persona_id: str = "Desconocido", descripcion: str = "") -> str:
    """
    ÚSALA PARA CREAR UNA NUEVA OPORTUNIDAD DE VENTA.
    Requiere: nombre.
    Opcional: monto (un número, ej. 60000).
    Opcional: etapa ("NEW", "SCREENING", "MEETING", "PROPOSAL", "CUSTOMER").
    Opcional: company_id, persona_id.
    Opcional: descripcion (Detalles del proyecto o notas de citas).
    """
    # Convertimos el monto a número de forma segura
    try:
        monto_num = float(str(monto).replace(",", ""))
    except (ValueError, TypeError):
        monto_num = 0.0
    monto_micros = int(monto_num * 1000000)

    payload = {
        "name": nombre,
        "amount": {
            "amountMicros": monto_micros,
            "currencyCode": moneda
        },
        "stage": etapa,
        "description": descripcion
    }
    
    # NUEVO: Vinculamos con la empresa y el cliente (pointOfContactId)
    # Bloqueamos palabras basura como "null", "none" o "desconocido"
    if company_id and str(company_id).lower() not in ['desconocido', 'null', 'none']: 
        payload["companyId"] = company_id
        
    if persona_id and str(persona_id).lower() not in ['desconocido', 'null', 'none']: 
        payload["pointOfContactId"] = persona_id

    respuesta = _twenty_api_request('POST', 'opportunities', payload=payload)

    if "error" in respuesta:
        return f"RESULTADO DE CREACIÓN: Ocurrió un error al crear la oportunidad. Detalles: {respuesta['error']}"

    nuevo_id = respuesta.get('data', {}).get('createOpportunity', {}).get('id') or respuesta.get('data', {}).get('id', 'Generado')
    
    return f"RESULTADO DE CREACIÓN: Oportunidad de venta creada exitosamente. El ID asignado es {nuevo_id} y su etapa inicial es {etapa}."
@tool("modificar_oportunidad")
def modificar_oportunidad(id_oportunidad: str, nombre: str, monto: str, moneda: str, etapa: str) -> str:
    """
    ÚSALA PARA ACTUALIZAR UNA OPORTUNIDAD DE VENTA EXISTENTE.
    Obligatorio: id_oportunidad.
    Para los campos que NO vas a cambiar, DEBES pasar exactamente la palabra "NO_CAMBIAR".
    IMPORTANTE: Los únicos valores válidos para 'etapa' son: "NEW", "SCREENING", "MEETING", "PROPOSAL", "CUSTOMER".
    """
    payload = {}
    
    if nombre and nombre != 'NO_CAMBIAR': 
        payload["name"] = nombre
    
    if etapa and etapa != 'NO_CAMBIAR': 
        payload["stage"] = etapa

    # Lógica combinada para el monto
    if (monto and monto != 'NO_CAMBIAR') or (moneda and moneda != 'NO_CAMBIAR'):
        payload["amount"] = {}
        if monto and monto != 'NO_CAMBIAR':
            try:
                payload["amount"]["amountMicros"] = int(float(str(monto).replace(",", "")) * 1000000)
            except (ValueError, TypeError):
                pass
        if moneda and moneda != 'NO_CAMBIAR':
            payload["amount"]["currencyCode"] = moneda

    if not payload:
        return "RESULTADO DE MODIFICACIÓN: No se enviaron campos nuevos para actualizar."

    respuesta = _twenty_api_request('PATCH', f'opportunities/{id_oportunidad}', payload=payload)

    if "error" in respuesta:
        return f"RESULTADO DE MODIFICACIÓN: Error al intentar actualizar la oportunidad: {respuesta['error']}"

    return "RESULTADO DE MODIFICACIÓN: La oportunidad ha sido actualizada exitosamente."

@tool("eliminar_oportunidad")
def eliminar_oportunidad(id_oportunidad: str) -> str:
    """
    ÚSALA ÚNICAMENTE PARA BORRAR UNA OPORTUNIDAD PERMANENTEMENTE.
    Requiere el id_oportunidad exacto.
    """
    respuesta = _twenty_api_request('DELETE', f'opportunities/{id_oportunidad}')

    if "error" in respuesta:
        return f"RESULTADO DE ELIMINACIÓN: No se pudo eliminar la oportunidad. Detalles: {respuesta['error']}"

    return "RESULTADO DE ELIMINACIÓN: La oportunidad ha sido eliminada permanentemente del sistema."