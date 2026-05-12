from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.crews.department import DepartamentoCRMCrew
import uuid
import os
from dotenv import load_dotenv
import time

# Cargar variables de entorno
load_dotenv()

app = FastAPI(
    title="Agentic CRM API",
    description="API REST para conectar el sistema de agentes CRM con orquestadores como n8n",
    version="1.0.0",
)

# Configuración de CORS para permitir conexiones desde n8n
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especifica el dominio de tu n8n
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacén de sesiones en memoria
# NOTA: En un entorno de producción con múltiples réplicas, esto debería estar en Redis
sesiones: dict[str, DepartamentoCRMCrew] = {}

# API Key para seguridad básica (definirla en el .env como API_SECRET_KEY)
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "tri-tec-secret-123")


class MensajeRequest(BaseModel):
    session_id: str = None  # ID de sesión opcional
    mensaje: str  # Mensaje del cliente


class MensajeResponse(BaseModel):
    session_id: str
    respuesta: str
    estado: str
    datos_acumulados: dict
    tiempo_ejecucion: str


@app.get("/")
async def root():
    return {"status": "online", "message": "Agentic CRM API is running"}


@app.post("/api/chat", response_model=MensajeResponse)
async def chat(req: MensajeRequest, x_api_key: str = Header(None)):
    # 1. Validar Seguridad
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="No autorizado. API Key inválida.")

    # 2. Gestionar Sesión
    # Si no envían session_id o no existe, creamos una nueva
    if not req.session_id or req.session_id not in sesiones:
        session_id = str(uuid.uuid4())
        sesiones[session_id] = DepartamentoCRMCrew()
        print(f"[NEW] Nueva sesion creada: {session_id}")
    else:
        session_id = req.session_id
        print(f"[EXISTING] Usando sesion existente: {session_id}")

    # 3. Procesar Solicitud
    start_time = time.time()
    try:
        departamento = sesiones[session_id]
        respuesta_final = departamento.procesar_solicitud(req.mensaje)
        end_time = time.time()
        tiempo_total_segundos = end_time - start_time
        
        # Formatear a minutos y segundos
        minutos = int(tiempo_total_segundos // 60)
        segundos = int(tiempo_total_segundos % 60)
        tiempo_formateado = f"{minutos}m {segundos}s" if minutos > 0 else f"{segundos}s"

        return MensajeResponse(
            session_id=session_id,
            respuesta=respuesta_final,
            estado=departamento.estado,
            datos_acumulados=departamento.datos_acumulados,
            tiempo_ejecucion=tiempo_formateado,
        )
    except Exception as e:
        print(f"[ERROR] Error procesando solicitud: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
