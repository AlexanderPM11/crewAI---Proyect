import os
from crewai.tools import tool

@tool("leer_faqs_empresa")
def leer_faqs_empresa() -> str:
    """
    ÚSALA SIEMPRE QUE EL CLIENTE PREGUNTE POR PRECIOS, SERVICIOS, TIEMPOS O QUÉ HACEMOS.
    Esta herramienta lee el documento oficial de Preguntas Frecuentes de la empresa.
    """
    ruta_archivo = os.path.join(os.getcwd(), 'faqs.txt')
    
    try:
        # El secreto está en el "encoding='utf-8'"
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
            return f"RESULTADO DE FAQS:\n{contenido}"
    except FileNotFoundError:
        return "Error: No se encontró el archivo faqs.txt. Dile al cliente que por el momento no tienes los precios a la mano."
    except Exception as e:
        return f"Error al leer FAQs: {str(e)}"