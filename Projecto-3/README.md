# Operaciones de Machine Learning
## Proyecto 3 - Nivel 3
**Pontificia Universidad Javeriana**

## Descripción del Proyecto

Este proyecto implementa un sistema completo de Machine Learning Operations (MLOps) utilizando tecnologías de contenedores y orquestación para el despliegue y monitoreo de modelos de machine learning.

## Arquitectura del Sistema

### Kubernetes y Monitoreo

Sistema de monitoreo implementado con Kubernetes para la observabilidad del sistema.

**Tecnologías:**
- Microk8s

**Servicios de Monitoreo:**
- **Grafana**: http://10.43.100.87:3010/
- **Prometheus**: http://10.43.100.87:3011/

> Para más detalles sobre la configuración de Kubernetes, consultar el [README de monitoreo](./monitoring/README.md)

### Recolección de Datos y Entrenamiento de Modelo

Pipeline de ML implementado con MLflow y Airflow para la gestión del ciclo de vida de modelos.

**Tecnologías:**
- MLflow
- Airflow

**Enlaces:**
- *Por definir*

### Desarrollo de API y Cliente

Aplicación web desarrollada con FastAPI y Streamlit para la interacción con el modelo.

**Tecnologías:**
- FastAPI
- Streamlit
- Locust

**Enlaces:**
- *Por definir*

## Resultados

*Sección en desarrollo - Los resultados del proyecto serán documentados aquí.*

## Integrantes del Equipo

- **Omar Gaston Chalas** 
- **Abel Albuez Sanchez**
- **Mauricio Morales**
