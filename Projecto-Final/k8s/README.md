# Cluster de aplicaciones

Documentación de la configuración del cluster de aplicaciones en Kubernetes.

## Desplegar Aplicaciones

1. Actualizar el docker compose con los valores reales (TODO)
2. Construir y taggear las imágenes al registry del cluster aalbuez

```sh
# Construir imágenes
docker build -t mlops-prediction-api:latest ./api
docker build -t mlops-prediction-ui:latest ./streamlit

# Taggear las imágenes
docker tag mlops-prediction-api:latest aalbuez/mlops-prediction-api:latest
docker tag mlops-prediction-ui:latest aalbuez/mlops-prediction-ui:latest

# Push
docker push aalbuez/mlops-prediction-api:latest
docker push aalbuez/mlops-prediction-ui:latest
```

3. Instalar kompose

```sh
sudo curl -L https://github.com/kubernetes/kompose/releases/download/v1.34.0/kompose-linux-amd64 -o /usr/local/bin/kompose
sudo chmod +x /usr/local/bin/kompose
```

4. Convertir docker compose (desde k8s)
```sh
mkdir k8s && cd k8s
kompose convert -f ../docker-compose.kompose.yml --namespace apps
```

5. Ejecutar inicio de servicio
```sh
kubectl -n apps apply -f .
```

6. Activar los servicios (desde k8s)
```sh
chmod +x init-forward.sh
./init-forward.sh
```

El script `init-forward.sh` en el directorio `k8s/` expone estos servicios mediante port-forward:
- API: `http://localhost:8001` (puerto interno 8000)
- Streamlit: `http://localhost:8003` (puerto interno 8501)

Los logs y PIDs de los procesos de port-forward se guardan en `./logs/`.

Para detener los port-forwards:
```sh
pkill -f 'kubectl port-forward'
# o
kill $(cat logs/api-forward.pid) $(cat logs/streamlit-forward.pid)
```

