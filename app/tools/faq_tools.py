import os
from crewai.tools import tool

@tool("leer_faqs_empresa")
def leer_faqs_empresa(busqueda: str = None) -> str:
    """
    Lee la base de conocimiento de Triple Tecnología.
    Pasa un término en 'busqueda' para filtrar información específica (precios, servicios, etc.).
    """
    ruta_archivo = os.path.join(os.getcwd(), 'faqs.md')
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
            
            if busqueda and busqueda.lower() != "todo":
                lineas = contenido.split('\n')
                resultados = [l for l in lineas if busqueda.lower() in l.lower()]
                if resultados:
                    return f"RESULTADOS PARA '{busqueda}':\n" + "\n".join(resultados[:20])
                return f"No se encontró información específica sobre '{busqueda}'. Aquí tienes un resumen general:\n{contenido[:500]}..."
            
            return f"--- BASE DE CONOCIMIENTO ---\n{contenido}\n--- FIN ---"
    except FileNotFoundError:
        return "Error: No se encontró el archivo faqs.txt. Dile al cliente que por el momento no tienes los precios a la mano."
    except Exception as e:
        return f"Error al leer FAQs: {str(e)}"