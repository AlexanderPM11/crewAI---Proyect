import os
from dotenv import load_dotenv
from crewai import LLM
from langchain_nvidia_ai_endpoints import ChatNVIDIA
import litellm          # <--- 1. IMPORTA LITELLM
#os.environ['LITELLM_LOG'] = 'DEBUG'
# Cargar variables de entorno
load_dotenv()

# ==========================================
# 1. MODELO LOCAL (OLLAMA)
# ==========================================
url_ollama = os.getenv("OLLAMA_URL", "http://localhost:11434")

local_llm = LLM(
    model="ollama/gemma4:e2b", # Prefijo 'ollama/'
    base_url=url_ollama
)

nvidia_llm = LLM(
    model="nvidia_nim/google/gemma-3n-e4b-it",
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)
# ==========================================
# LLM ACTIVO PARA LA APLICACIÓN
# ==========================================
# Cambia esta variable para usar un modelo diferente en toda tu app
llm_activo = nvidia_llm # Cambia a local_llm, gemini_llm, etc.