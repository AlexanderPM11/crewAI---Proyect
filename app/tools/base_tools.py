import os
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool

# Cargar variables de entorno
load_dotenv()

def _twenty_api_request(method: str, endpoint: str, params=None, payload=None) -> dict:
    """Maneja las peticiones a TwentyCRM. Retorna un dict o lanza una excepción."""
    url = f"{os.getenv('TWENTY_URL')}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {os.getenv('TWENTY_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=payload)
        elif method == 'PATCH': # Para modificar
            response = requests.patch(url, headers=headers, json=payload)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
            
        if not response.ok:
            return {"error": f"HTTP {response.status_code}. Detalles: {response.text}"}
            
        # El DELETE suele devolver 204 No Content sin JSON
        if method == 'DELETE' and response.status_code == 204:
            return {"status": "success"}
            
        return response.json()
    except Exception as e:
        return {"error": str(e)}