FROM python:3.9-slim

WORKDIR /app

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY . .

# Crear directorio para modelos
RUN mkdir -p /app/models

# Exponer puerto para la API
EXPOSE 8000

# Comando por defecto para la API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]