import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
import uuid
import time
from app.crews.department import DepartamentoCRMCrew
from app.core.database import guardar_mensaje, obtener_historial

# Cargar variables de entorno
load_dotenv()
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "tri-tec-secret-123")

app = FastAPI(title="Agentic CRM API")

# Modelo de entrada
class MensajeRequest(BaseModel):
    mensaje: str
    session_id: Optional[str] = None

# Modelo de respuesta
class MensajeResponse(BaseModel):
    session_id: str
    respuesta: str
    estado: str
    datos_acumulados: dict
    tiempo_ejecucion: str

# Almacén de sesiones (ahora solo para mantener el objeto de la crew en el turno actual)
# La memoria a largo plazo viene de Supabase
sessions = {}

@app.post("/chat", response_model=MensajeResponse)
async def chat(request: MensajeRequest, x_api_key: str = Header(...)):
    # Validar API Key
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Acceso denegado: API Key inválida")
    
    start_time = time.time()
    
    # 1. Gestionar session_id
    if not request.session_id:
        session_id = str(uuid.uuid4())
    else:
        session_id = request.session_id

    try:
        # 2. PERSISTENCIA: Guardar mensaje del usuario en la DB
        guardar_mensaje(session_id, "user", request.mensaje)

        # 3. Cargar historial de la DB (últimos 10 mensajes)
        historial_previo = obtener_historial(session_id, limite=10)

        # 4. Obtener o crear instancia de la Crew con el historial cargado
        # Nota: Siempre creamos una nueva instancia para asegurar que tiene el historial fresco de la DB
        crew = DepartamentoCRMCrew(initial_history=historial_previo)
        
        # 5. Procesar solicitud
        respuesta_final = crew.procesar_solicitud(request.mensaje)

        # 6. PERSISTENCIA: Guardar respuesta del asistente en la DB
        guardar_mensaje(session_id, "assistant", respuesta_final)

        # Calcular tiempo de ejecución
        end_time = time.time()
        duracion = end_time - start_time
        if duracion >= 60:
            tiempo_str = f"{int(duracion // 60)}m {int(duracion % 60)}s"
        else:
            tiempo_str = f"{int(duracion)}s"

        return MensajeResponse(
            session_id=session_id,
            respuesta=respuesta_final,
            estado=crew.estado,
            datos_acumulados=crew.datos_acumulados,
            tiempo_ejecucion=tiempo_str
        )

    except Exception as e:
        print(f"[ERROR] Error procesando solicitud: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
