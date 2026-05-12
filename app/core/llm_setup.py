import os
from dotenv import load_dotenv
from crewai import LLM

# Cargar variables de entorno
load_dotenv()

# ==========================================
# CONFIGURACIONES DE PROVEEDORES
# ==========================================

# 1. MODELO LOCAL (OLLAMA)
url_ollama = os.getenv("OLLAMA_URL", "http://localhost:11434")
ollama_model = os.getenv("OLLAMA_MODEL", "ollama/gemma4:e2b")
local_llm = LLM(
    model=ollama_model,
    base_url=url_ollama
)

# 2. NVIDIA NIM
nvidia_model = os.getenv("NVIDIA_MODEL", "nvidia_nim/google/gemma-3n-e4b-it")
nvidia_llm = LLM(
    model=nvidia_model,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

# 3. OPENAI
openai_model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
openai_llm = LLM(
    model=openai_model,
    api_key=os.getenv("OPENAI_API_KEY")
)

# 4. GOOGLE GEMINI
gemini_model = os.getenv("GEMINI_MODEL", "gemini/gemini-1.5-flash")
gemini_llm = LLM(
    model=gemini_model,
    api_key=os.getenv("GEMINI_API_KEY")
)

# ==========================================
# SELECCIÓN DINÁMICA DEL MODELO
# ==========================================
# Opciones: 'ollama', 'nvidia', 'openai', 'gemini'
provider = os.getenv("MODEL_PROVIDER", "nvidia").lower()

if provider == "ollama":
    llm_activo = local_llm
    modelo_nombre = ollama_model
elif provider == "openai":
    llm_activo = openai_llm
    modelo_nombre = openai_model
elif provider == "gemini":
    llm_activo = gemini_llm
    modelo_nombre = gemini_model
else:
    llm_activo = nvidia_llm
    modelo_nombre = nvidia_model

print(f"[LLM] Usando proveedor: {provider} | Modelo: {modelo_nombre}")