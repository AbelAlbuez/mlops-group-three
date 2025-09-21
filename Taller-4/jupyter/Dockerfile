# Base image con JupyterLab
FROM jupyter/scipy-notebook:python-3.11

# Cambiar a root para instalar paquetes del sistema
USER root

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    awscli \
    default-libmysqlclient-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Volver al usuario jovyan (usuario por defecto de Jupyter)
USER jovyan

# Actualizar pip
RUN pip install --upgrade pip

# Instalar dependencias de Python
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Configurar directorio de trabajo
WORKDIR /home/jovyan/work

# Exponer puerto de JupyterLab
EXPOSE 8888

# Comando por defecto (heredado de la imagen base)
CMD ["start-notebook.sh"]