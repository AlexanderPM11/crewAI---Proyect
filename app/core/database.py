import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(url, key)

def guardar_mensaje(session_id: str, role: str, content: str):
    """Guarda un mensaje en la base de datos."""
    try:
        supabase.table("chat_history").insert({
            "session_id": session_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        print(f"[DB ERROR] No se pudo guardar el mensaje: {e}")

def obtener_historial(session_id: str, limite: int = 10):
    """Obtiene los últimos mensajes de una sesión."""
    try:
        response = supabase.table("chat_history") \
            .select("role", "content") \
            .eq("session_id", session_id) \
            .order("created_at", desc=False) \
            .limit(limite) \
            .execute()
        
        # Formatear para el agente
        historial = []
        for msg in response.data:
            prefix = "Cliente" if msg["role"] == "user" else "Asistente"
            historial.append(f"{prefix}: {msg['content']}")
            
        return historial
    except Exception as e:
        print(f"[DB ERROR] No se pudo obtener el historial: {e}")
        return []
