import os
from crewai.tools import tool

@tool("leer_faqs_empresa")
def leer_faqs_empresa() -> str:
    """
    ÚSALA SIEMPRE QUE EL CLIENTE PREGUNTE POR:
    - Precios de productos (Kinetic POS, Icarus).
    - Servicios que ofrecemos (Desarrollo, Outsourcing, Cloud, Asesoría).
    - Horarios, ubicación o contacto.
    - Tecnologías que manejamos (.NET, React, Flutter, etc.).
    - Metodología de trabajo.
    Esta herramienta lee la base de conocimiento oficial de Triple Tecnología.
    """
    ruta_archivo = os.path.join(os.getcwd(), 'faqs.md')
    
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            contenido = archivo.read()
            return f"--- BASE DE CONOCIMIENTO (TRIPLE TECNOLOGÍA) ---\n{contenido}\n--- FIN DE LA BASE DE CONOCIMIENTO ---"
    except FileNotFoundError:
        return "Error: No se encontró el archivo faqs.txt. Dile al cliente que por el momento no tienes los precios a la mano."
    except Exception as e:
        return f"Error al leer FAQs: {str(e)}"