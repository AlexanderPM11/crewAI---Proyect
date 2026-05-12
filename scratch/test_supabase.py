import os
import uuid
from supabase import create_client
from dotenv import load_dotenv

# Cargar variables del .env
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"--- Probando conexión Final ---")

try:
    supabase = create_client(url, key)
    
    # Generamos un UUID real para la prueba
    test_session = str(uuid.uuid4())
    
    test_data = {
        "session_id": test_session,
        "role": "system",
        "content": "Prueba final con UUID"
    }
    
    print(f"Intentando insertar en 'chat_history' con session_id: {test_session}...")
    response = supabase.table("chat_history").insert(test_data).execute()
    
    print("✅ ¡TODO FUNCIONA PERFECTAMENTE!")
    print(f"Registro creado: {response.data}")

except Exception as e:
    print(f"\n❌ ERROR:")
    print(str(e))
