import os
from crewai.tools import tool

@tool("leer_faqs_empresa")
def leer_faqs_empresa(tema: str = None) -> str:
    """
    Busca información en la base de conocimientos.
    Argumento 'tema': palabra clave (precios, servicios, contacto, etc.).
    """
    ruta_archivo = os.path.join(os.getcwd(), 'faqs.md')
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
            
            if tema and tema.lower() != "todo":
                lineas = contenido.split('\n')
                resultados = [l for l in lineas if tema.lower() in l.lower()]
                if resultados:
                    return f"RESULTADOS PARA '{tema}':\n" + "\n".join(resultados[:25])
                return f"No encontré '{tema}'. Resumen:\n{contenido[:500]}..."
            
            return f"--- BASE DE CONOCIMIENTO ---\n{contenido}\n--- FIN ---"
    except FileNotFoundError:
        return "Error: No se encontró el archivo faqs.txt. Dile al cliente que por el momento no tienes los precios a la mano."
    except Exception as e:
        return f"Error al leer FAQs: {str(e)}"