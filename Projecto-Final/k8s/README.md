# Cluster de aplicaciones

Esta es la documentación de la configuración realizada en el cluster de aplicaciones en Kubernetes.

## Desplegar Aplicaciones

1. Actualizar el docker compose con los valores reales # TODO
2. construir y taggear las imagenes al registry del cluister aalbuez

```sh
# Contruir images
docker build -t mlops-prediction-api:latest ./api
docker build -t mlops-prediction-ui:latest ./streamlit


# Taggear las images
docker tag mlops-prediction-api:latest aalbuez/mlops-prediction-api:latest
docker tag mlops-prediction-ui:latest aalbuez/mlops-prediction-ui:latest

# Push
docker push aalbuez/mlops-prediction-api:latest
docker push aalbuez/mlops-prediction-ui:latest
```

4. instalar kompose

```sh
sudo curl -L https://github.com/kubernetes/kompose/releases/download/v1.34.0/kompose-linux-amd64 -o /usr/local/bin/kompose
sudo chmod +x /usr/local/bin/kompose
```

5. Convertir docker compose  (desde k8s)
```sh
mkdir k8s && cd k8s
kompose convert -f ../docker-compose.kompose.yml --namespace apps
```
6. Ejecutar inicio de servicio
```sh
kubectl -n apps apply -f .

```

7. activar los servicios (desde k8s)
```sh
chmod +x init-forward.sh
./init-forward.sh
```

El script `init-forward.sh` en el directorio `k8s/` expone los siguientes servicios de aplicaciones mediante port-forward:
- **API**: `http://localhost:8001` (puerto interno 8000)
- **Streamlit**: `http://localhost:8003` (puerto interno 8501)

Los logs y PIDs de los procesos de port-forward se guardan en el directorio `./logs/`.

Para detener los port-forwards de las aplicaciones:
```sh
pkill -f 'kubectl port-forward'
# o
kill $(cat logs/api-forward.pid) $(cat logs/streamlit-forward.pid)
```

