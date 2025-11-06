FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Exponer puerto
EXPOSE 8501

# Comando para ejecutar
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]