# Configuración del Proyecto

Este documento explica cómo configurar el entorno de desarrollo local para este proyecto de Python, aislando las dependencias mediante un entorno virtual.

## Requisitos Previos
Asegúrate de tener **Python 3.7+** instalado en tu sistema. Puedes verificarlo ejecutando el siguiente comando en tu terminal:
```bash
python --version
# o
python3 --version
```

---

## Instrucciones de Instalación

### 1. Crear un Entorno Virtual
Un entorno virtual te permite mantener las dependencias de este proyecto separadas de otros proyectos en tu máquina.

Abre tu terminal, navega hasta la carpeta raíz del proyecto y ejecuta:

**En Windows:**
```bash
python -m venv venv
```

**En macOS y Linux:**
```bash
python3 -m venv venv
```
*(Esto creará una nueva carpeta llamada `venv` en tu proyecto).*

### 2. Activar el Entorno Virtual
Debes activar el entorno virtual cada vez que vayas a trabajar en el proyecto.

**En Windows (Símbolo del sistema / CMD):**
```cmd
venv\Scripts\activate.bat
```

**En Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**En macOS y Linux:**
```bash
source venv/bin/activate
```
*Sabrás que está activado porque el nombre del entorno (`(venv)`) aparecerá al principio de la línea de tu terminal.*

### 3. Instalar las Librerías
Con el entorno virtual activado, procede a instalar todas las dependencias listadas en el archivo `requirements.txt`:

```bash
pip install -r requirements.txt
```
*Este comando descargará e instalará herramientas como `crewai`, `fastapi`, `requests`, entre otras, únicamente dentro de este entorno.*

---

## Notas Adicionales
* **Para desactivar el entorno virtual:** Cuando termines de trabajar y quieras volver al entorno global de tu sistema, simplemente ejecuta el comando:
  ```bash
  deactivate
  ```
* **Gitignore:** Asegúrate de que la carpeta `venv` esté incluida en tu archivo `.gitignore` para no subir los archivos del entorno virtual a tu repositorio (ya que pesan mucho y dependen del sistema operativo de cada desarrollador).


## Ejemplo ENV

# Configuración de TwentyCRM
TWENTY_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzNjc0NzRdfhtngtrfnrtnnrLCJ0eXBlIjoiQVBJX0tFWSIsIndvcmtzcGFjZUlkIjoiMzY3NDc0YmMtNTVjNC00NmYxLWFhODQtZmRmODYzMzY4MjU3IiwiaWF0IjoxNzc3NDc3NDcxLCJleHAiOjQ5MzEwNzc0NzAsImp0aSI6ImQwNDM3YmZmLTg4OTgtNGFlMS04ZDI5LWUxMmYwZDMzNzJjMCJ9.jhsv3AgB_zPOWYHHxYCEjVScL8yGT4bkiTqAwga33pk"
TWENTY_URL="https://app-crm.tripletecnologia.com/rest/"

# Configuración de Ollama Local
OLLAMA_URL="http://10.0.0.106:11434"

# Configuración NVIDIA NIM
NVIDIA_API_KEY="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"