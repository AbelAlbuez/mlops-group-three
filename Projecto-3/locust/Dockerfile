FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto de Locust
EXPOSE 8089

# Comando para ejecutar (se puede sobrescribir)
CMD ["locust", "-f", "locustfile.py"]