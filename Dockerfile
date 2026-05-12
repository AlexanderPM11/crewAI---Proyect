# Usa una imagen de Python ligera y estable
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y permite ver logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema necesarias para compilar algunas librerías de Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia el archivo de requerimientos primero para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido del proyecto al directorio de trabajo
COPY . .

# Expone el puerto 8000 (puerto por defecto de nuestra API)
EXPOSE 8000

# Comando para iniciar la aplicación usando Uvicorn
# Se usa api:app porque el archivo principal de la API es api.py
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
